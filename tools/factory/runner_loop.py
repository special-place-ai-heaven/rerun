#!/usr/bin/env python3
"""The factory runner loop (rerun#60 chunk C7). Plain code, no model. Commands: run | once | enqueue JOB STAGE.
Start: ensure_triggers, open the store, resolve unfinished fires. Every poll_s: read the run row over HTTP for every
running fire (the row is the truth, no events), record ends in the store, apply limits.run_outcome (CANCEL -> cancel;
error/RESTARTED -> fire again at most once per stage, then failed), and start the next queued stage by firing its trigger
with the packet payload (intent row committed before the fire). The queue lives in the store (kv, keys 'queue:...').
SIGTERM stops the loop between ticks. The engine key and trigger tokens are never printed."""
import argparse, json, os, signal, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E, limits as L, store as S, trigger as T

POLL_S = 30
QP = "queue:"


def log(msg):
    print("runner: " + msg, flush=True)


def store_path(cfg):
    return cfg.get("store_file") or os.path.join(os.environ.get("FACTORY_DATA_DIR", "/state"), "ledger.db")


def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


# ---- queue (rows in kv: job, 'queue:<seq>:<stage>', JSON {chunk, payload}) ----
def enqueue(st, job, stage, chunk="", payload=None):
    """Queue a stage. The packet payload defaults to {job, stage, chunk}."""
    key = "%s%013d:%s" % (QP, int(time.time() * 1000), stage)
    val = json.dumps({"chunk": chunk, "payload": payload or {"job": job, "stage": stage, "chunk": chunk}})
    st.set(job, key, val)
    return key


def enqueue_file(path, job, stage, chunk="", payload=None):
    """Queue from the CLI while the loop runs: its own connection (the loop holds the store's writer lock; WAL + busy wait)."""
    import sqlite3
    db = sqlite3.connect(path, timeout=30, isolation_level=None)
    try:
        db.execute("CREATE TABLE IF NOT EXISTS kv(job TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, PRIMARY KEY(job, k))")
        key = "%s%013d:%s" % (QP, int(time.time() * 1000), stage)
        val = json.dumps({"chunk": chunk, "payload": payload or {"job": job, "stage": stage, "chunk": chunk}})
        db.execute("INSERT INTO kv VALUES(?,?,?) ON CONFLICT(job,k) DO UPDATE SET v=excluded.v", (job, key, val))
    finally:
        db.close()
    return key


def queued(st):
    return [(r["job"], r["k"], json.loads(r["v"])) for r in
            st.db.execute("SELECT job,k,v FROM kv WHERE k LIKE 'queue:%' ORDER BY k")]


def _stage_of(key):
    return key.split(":", 2)[2]


class Runner:
    def __init__(self, eng, st, cfg, tokens, clock=time.time):
        self.eng, self.st, self.cfg, self.tokens, self.clock = eng, st, cfg, tokens, clock
        self.by_slug = {e["slug"]: e for e in cfg["triggers"]}
        self.by_stage = {e["stage"]: e for e in cfg["triggers"]}

    # -- one tick --
    def tick(self):
        self.resolve_pending()
        for f in self.st.running():
            try:
                self.check(f)
            except (E.EngineError, T.TriggerError) as e:
                log("read of run %s failed, will retry: %s" % (f["run_id"], e))
        self.start_queued()

    def _agent(self, f):
        e = self.by_slug.get(f["slug"])
        return e["agent"] if e else None

    def resolve_pending(self):
        """An intent with no run id (crash between intent and fire): find its run by trigger slug, else fail it after a
        few ticks. Never fired again from here."""
        for f in self.st.pending():
            agent = self._agent(f)
            if not agent:
                self.st.abandon(f["id"], "no trigger entry for slug")
                continue
            try:
                rows = [T.map_run(r) for r in self.eng.list_runs(agent)]
            except E.EngineError as e:
                log("cannot list runs of %s: %s" % (agent, e))
                continue
            taken = {r[0] for r in self.st.db.execute("SELECT run_id FROM fires WHERE run_id IS NOT NULL")}
            rows = [r for r in rows if r and r["id"] not in taken]
            what, val = L.resolve_pending(f["intent_at"], f["slug"], rows, self.clock(), self.cfg.get("poll_s", POLL_S))
            if what == "RUN":
                self.st.fired(f["id"], val)
            elif what == "FAILED":
                self.st.abandon(f["id"], val)
                log("fire %d abandoned: %s" % (f["id"], val))

    def _steps(self, agent, f, row):
        tokens = (row.get("input_tokens") or 0) + (row.get("output_tokens") or 0)
        last = None
        try:
            for s in self.eng.run_steps(agent, f["run_id"]):
                t = s.get("finishedAt") or s.get("startedAt") or s.get("createdAt")
                if t and (last is None or L.ts(t) > L.ts(last)):
                    last = t
            ok = True
        except E.EngineError:
            ok = False
        # unknown step times must not read as a stall: use now
        return {"last_step_at": last or iso(self.clock()), "tokens": tokens} if ok else {"tokens": tokens}

    def check(self, f):
        agent = self._agent(f)
        if not agent:
            self.st.close_run(f["run_id"], "failed", error="no trigger entry for slug")
            return
        row = T.read_run(self.eng, agent, f["run_id"])
        steps = self._steps(agent, f, row) if row and row.get("status") == "running" else None
        what, why = L.run_outcome(row, self.clock(), steps, self.cfg)
        tin, tout = (row or {}).get("input_tokens") or 0, (row or {}).get("output_tokens") or 0
        rid = f["run_id"]
        if what == "RUNNING":
            return
        if what == "DONE":
            self.st.close_run(rid, "done", iso(self.clock()), tin, tout)
        elif what == "CANCEL":
            self.eng.cancel(agent, rid)
            self.st.close_run(rid, "cancelled", iso(self.clock()), tin, tout, why)
            log(why)
        elif what in ("REFIRE_ONCE", "RESTARTED"):
            n = self.st.refires(f["job"], f["chunk"], f["stage"])
            ok = (n < 1) if what == "REFIRE_ONCE" else L.restart(n)[0] == "REFIRE"
            err = why or L.RESTARTED
            if ok:
                self.st.close_run(rid, "error", iso(self.clock()), tin, tout, err)
                self.requeue(f)
                log("run %s ended in error, stage %s queued again once" % (rid, f["stage"]))
            else:
                self.st.close_run(rid, "failed", iso(self.clock()), tin, tout, err)
                log("run %s failed: refire already used" % rid)
        else:  # FAILED, MISSING
            self.st.close_run(rid, "failed", iso(self.clock()), tin, tout, why)

    def requeue(self, f):
        payload = {"job": f["job"], "stage": f["stage"], "chunk": f["chunk"]}
        st = self.st.get_all(f["job"]).get("payload:" + f["stage"])
        if st:
            payload = json.loads(st)
        enqueue(self.st, f["job"], f["stage"], f["chunk"], payload)

    def start_queued(self):
        busy = {f["job"] for f in self.st.pending() + self.st.running()}
        for job, key, item in queued(self.st):
            if job in busy:
                continue
            stage = _stage_of(key)
            ent = self.by_stage.get(stage)
            if not ent:
                log("no trigger for stage %s of job %s, dropped" % (stage, job))
                self.st.db.execute("DELETE FROM kv WHERE job=? AND k=?", (job, key))
                continue
            total = self.st.db.execute("SELECT COUNT(*) FROM fires WHERE job=?", (job,)).fetchone()[0]
            if L.may_fire(total)[0] != "FIRE":
                log("job %s hit the fire cap, stage %s dropped" % (job, stage))
                self.st.db.execute("DELETE FROM kv WHERE job=? AND k=?", (job, key))
                continue
            token = self.tokens.get("%s/%s" % (ent["agent"], ent["slug"]))
            if not token:
                log("no token for %s, skipped" % ent["slug"])
                continue
            chunk = item.get("chunk", "")
            self.st.set(job, "payload:" + stage, json.dumps(item["payload"]))
            db = self.st.db
            db.execute("BEGIN IMMEDIATE")  # intent in, queue row out, one commit, before the fire
            try:
                fid = self.st.intent(job, chunk, stage, ent.get("coworker", ""), ent["slug"])
                db.execute("DELETE FROM kv WHERE job=? AND k=?", (job, key))
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
            busy.add(job)
            try:
                run_id, _ = T.fire(self.eng, ent["agent"], ent["slug"], token, item["payload"])
            except T.TriggerError as e:
                log("fire of %s failed (kept as intent, resolved next tick): %s" % (ent["slug"], e))
                continue
            self.st.fired(fid, run_id)
            log("fired stage %s of job %s: run %s" % (stage, job, run_id))


def build(cfg=None, eng=None, clock=time.time):
    cfg = cfg if cfg is not None else T.load_config()
    eng = eng or E.Engine()
    tokens = T.ensure_triggers(eng, cfg)
    st = S.Store(store_path(cfg))
    return Runner(eng, st, cfg, tokens, clock)


def run(r, stop, poll_s):
    log("started")
    while not stop.is_set():
        try:
            r.tick()
        except (E.EngineError, T.TriggerError) as e:
            log("tick failed: %s" % e)
        stop.wait(poll_s)
    log("stopped")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="runner_loop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    sub.add_parser("once")
    en = sub.add_parser("enqueue")
    en.add_argument("job")
    en.add_argument("stage")
    en.add_argument("--chunk", default="")
    en.add_argument("--payload-file", help="JSON file used as the packet payload")
    a = ap.parse_args(argv)
    cfg = T.load_config()
    if a.cmd == "enqueue":
        payload = None
        if a.payload_file:
            with open(a.payload_file, encoding="utf-8") as f:
                payload = json.load(f)
        enqueue_file(store_path(cfg), a.job, a.stage, a.chunk, payload)
        print("queued %s %s" % (a.job, a.stage))
        return 0
    try:
        r = build(cfg)
    except (E.EngineError, T.TriggerError, RuntimeError) as e:
        print("runner: cannot start: %s" % e, file=sys.stderr)
        return 1
    if a.cmd == "once":
        r.tick()
        r.st.close()
        return 0
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    run(r, stop, cfg.get("poll_s", POLL_S))
    r.st.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
