#!/usr/bin/env python3
"""The factory runner loop (rerun#60 chunk C7). Plain code, no model. Commands: setup | run | once | enqueue JOB STAGE.
Start: ensure_triggers, open the store, resolve unfinished fires. Every poll_s: read the run row over HTTP for every
running fire (the row is the truth, no events), record ends in the store, apply limits.run_outcome (CANCEL -> cancel;
error/RESTARTED -> fire again at most once per stage, then failed), and start the next queued stage by firing its trigger
with the packet payload (intent row committed before the fire). The queue is the store's queue table; `enqueue` only drops a JSON request file in the inbox dir of the runner volume (atomic rename) and the loop ingests it each tick, so the loop is the only process that opens the store. A trigger entry may carry its own run_limit_s/stall_s/token_cap.
SIGTERM stops the loop between ticks. The engine key and trigger tokens are never printed."""
import argparse, json, os, signal, subprocess, sys, tempfile, threading, time, uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import applypatch as AP, checkout as CO, engine as E, factory as F, limits as L, publish as PB, followups as FU, readyq as RQ, store as S, testrun as TR, trigger as T, wake

POLL_S = 30
INBOX_NAME = "inbox"

def log(msg):
    print("runner: " + msg, flush=True)

def store_path(cfg):
    return cfg.get("store_file") or os.path.join(os.environ.get("FACTORY_DATA_DIR", "/state"), "ledger.db")

STATE_NAME = "runner-state.json"
STUB = {"name": "stub", "provider": "custom", "baseUrl": "http://stub-model:8080/v1", "models": ["stub-fast", "stub-hold"]}
DEFAULT_MODEL = "stub-fast"

class NeedsSetup(RuntimeError):
    """runner.json names a coworker the state file has no id for yet."""

def state_path(cfg):
    """The state file (coworker ids written by `setup`): runner.json key state_file, else beside the ledger in the runner volume."""
    return cfg.get("state_file") or os.path.join(os.path.dirname(store_path(cfg)), STATE_NAME)

def read_state(cfg):
    try:
        with open(state_path(cfg), encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        raise RuntimeError("cannot read the state file; run setup again") from None
    return data if isinstance(data, dict) else {}

def write_state(cfg, state):
    path = state_path(cfg)
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".state-", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, sort_keys=True, indent=1)
    os.replace(tmp, path)

def resolve(cfg, state, strict=True):
    """A copy of cfg whose trigger entries without an `agent` take it from state['agents'][entry['agent_name']].
    runner.json is a template (no ids); an entry that cannot be resolved raises RuntimeError, or is left out when not strict."""
    out = dict(cfg)
    out["triggers"] = []
    for e in cfg["triggers"]:
        e = dict(e)
        if not e.get("agent"):
            aid = (state.get("agents") or {}).get(e.get("agent_name") or e["stage"])
            if not aid:
                if strict:
                    raise NeedsSetup("no coworker id for stage %s: run `runner_loop.py setup` first" % e["stage"])
                continue
            e["agent"] = aid
        out["triggers"].append(e)
    return out

def load_runtime(cfg=None, strict=True):
    """runner.json resolved with the state file: what `run`, `once` and status_report all read (one config, one store path)."""
    cfg = cfg if cfg is not None else T.load_config()
    return resolve(cfg, read_state(cfg), strict)

def setup(eng, cfg):
    """Create or reuse, in this order: the stub's `custom` connection (set as the box default), one coworker per trigger entry
    that names an `agent_name`, then the triggers. Ids go to the state file. A second run creates nothing. Returns the lines to print."""
    out, state = [], read_state(cfg)
    listing = eng._call("GET", "/connections")
    conn = next((c for c in listing.get("connections") or [] if c.get("name") == STUB["name"] and c.get("provider") == "custom"), None)
    if conn is None:
        conn = eng._call("POST", "/connections", payload=dict(STUB))
        out.append("stub connection created: %s" % conn["id"])
        listing = eng._call("GET", "/connections")
    else:
        out.append("stub connection reused: %s" % conn["id"])
    cur = listing.get("default") or {}
    if cur.get("connectionId") != conn["id"] or cur.get("model") != DEFAULT_MODEL:
        eng._call("PUT", "/connections/default", payload={"connectionId": conn["id"], "model": DEFAULT_MODEL})
        out.append("stub connection set as default, model %s" % DEFAULT_MODEL)
    index = {a.get("id"): a for a in eng._call("GET", "/agents").get("agents") or []}
    by_name = {a.get("name"): a for a in index.values()}
    agents = dict(state.get("agents") or {})
    for e in cfg["triggers"]:
        name = e.get("agent_name")
        if e.get("agent") or not name:
            continue
        aid = agents.get(name)
        if aid in index:
            out.append("coworker %s reused: %s" % (name, aid))
        elif name in by_name:
            aid = by_name[name]["id"]
            out.append("coworker %s reused: %s" % (name, aid))
        else:
            row = eng._call("POST", "/agents", payload={"config": {
                "name": name, "description": "Factory stage coworker (dev engine, stub model)",
                "connectionId": conn["id"], "provider": "custom", "model": e.get("model") or DEFAULT_MODEL}})
            aid = row["id"]
            by_name[name] = row
            out.append("coworker %s created: %s" % (name, aid))
        agents[name] = aid
    state = {"connection": conn["id"], "agents": agents}
    write_state(cfg, state)
    T.ensure_triggers(eng, resolve(cfg, state))
    out.append("triggers ensured")
    return out

def iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))

# ---- queue (store.queue table; the CLI writes inbox request files) ----
def inbox_path(cfg):
    """Where `enqueue` drops request files: <runner volume>/inbox, beside the ledger. The loop is the only store writer."""
    return cfg.get("inbox_dir") or os.path.join(os.path.dirname(store_path(cfg)), INBOX_NAME)

def enqueue(inbox, job, stage, chunk="", payload=None):
    """Queue a stage from the CLI: one small JSON request file in the inbox dir, written to a temp name and renamed
    (atomic). No store access: the loop ingests the file at its next tick. The packet payload defaults to {job, stage, chunk}."""
    os.makedirs(inbox, exist_ok=True)
    body = {"job": job, "stage": stage, "chunk": chunk, "payload": payload or {"job": job, "stage": stage, "chunk": chunk}}
    name = "%013d-%s.json" % (int(time.time() * 1000), uuid.uuid4().hex[:8])
    fd, tmp = tempfile.mkstemp(prefix=".req-", dir=inbox)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(body, f)
    os.replace(tmp, os.path.join(inbox, name))
    return name

def ingest(st, inbox):
    """Move every request file of the inbox into the store's queue (oldest name first), then delete the file.
    An unreadable or incomplete file is renamed *.bad and skipped. Returns the number queued."""
    try:
        names = sorted(n for n in os.listdir(inbox) if n.endswith(".json") and not n.startswith("."))
    except FileNotFoundError:
        return 0
    n = 0
    for name in names:
        path = os.path.join(inbox, name)
        try:
            with open(path, encoding="utf-8") as f:
                req = json.load(f)
            job, stage = str(req["job"]), str(req["stage"])
            payload = req.get("payload")
            if payload is not None and not isinstance(payload, dict):
                raise ValueError("payload is not an object")
        except (OSError, ValueError, KeyError, TypeError) as e:
            log("bad request file %s: %s" % (name, type(e).__name__))
            try:
                os.replace(path, path + ".bad")
            except OSError:
                pass
            continue
        st.enqueue(job, stage, str(req.get("chunk") or ""), payload)
        os.unlink(path)
        n += 1
    return n

class Runner:
    def __init__(self, eng, st, cfg, tokens, clock=time.time, open_pr=lambda *a: None, evidence=None, issues=None):
        self.open_pr, self.evidence, self.issues = open_pr, evidence, issues
        self.eng, self.st, self.cfg, self.tokens, self.clock = eng, st, cfg, tokens, clock
        self.by_slug = {e["slug"]: e for e in cfg["triggers"]}
        self.by_stage = {e["stage"]: e for e in cfg["triggers"]}

    # -- one tick --
    def tick(self):
        ingest(self.st, inbox_path(self.cfg))
        self.resolve_pending()
        for f in self.st.running():
            try:
                self.check(f)
            except (E.EngineError, T.TriggerError) as e:
                log("read of run %s failed, will retry: %s" % (f["run_id"], e))
        self.sweep_leases()
        self.start_queued()
        self.start_ready()

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
            taken = self.st.known_run_ids()
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
        # no step yet: last_step_at stays None and limits counts the stall from the run's start, never from now
        return {"last_step_at": last, "tokens": tokens} if ok else {"tokens": tokens}

    def check(self, f):
        agent = self._agent(f)
        if not agent:
            self.st.close_run(f["run_id"], "failed", error="no trigger entry for slug")
            return
        row = T.read_run(self.eng, agent, f["run_id"])
        steps = self._steps(agent, f, row) if row and row.get("status") == "running" else None
        what, why = L.run_outcome(row, self.clock(), steps, L.stage_cfg(self.cfg, self.by_slug.get(f["slug"])))
        tin, tout = (row or {}).get("input_tokens") or 0, (row or {}).get("output_tokens") or 0
        rid = f["run_id"]
        if what == "RUNNING":
            return
        if what == "DONE" and self.lease_closed(f):
            self.st.close_run(rid, "discarded", iso(self.clock()), tin, tout, "result under a closed lease")
            log("run %s result discarded: lease of chunk %s closed" % (rid, f["chunk"]))
        elif what == "DONE":
            if f["stage"] == "build" and f["chunk"] and "published:" + f["chunk"] not in self.st.get_all(f["job"]):
                self.finish_build(f)
            ev = self.evidence(f) if self.evidence else ("OK", "")
            if ev[0] != "OK":
                return  # the run ended but no evidence yet: stays running, read again next tick
            if f["stage"] == "review" and self.issues:
                self.follow_up(f["job"], ev[1])
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

    def follow_up(self, job, verdict):
        """One issue per follow-up note of a done review; the keys already opened live in the job kv (the client cannot list)."""
        kv = self.st.get_all(job)
        done = {k[9:] for k in kv if k.startswith("followup:")}
        try:
            for k in FU.create(self.issues, FU.notes(verdict, job), done):
                self.st.set(job, "followup:" + k, "1")
        except (OSError, RuntimeError) as e:
            log("follow-up issues for %s stopped: %s" % (job, type(e).__name__))

    def finish_build(self, f):
        """A build run ended: check out base and head, apply the chunk's patch, run its done-test (fails on base, passes on
        head), publish only the chunk's paths. Job kv keys: repo_url, base, base_branch, title, patch:<chunk>, test:<chunk>."""
        job, chunk = f["job"], f["chunk"]
        kv, paths = self.st.get_all(job), self.st.get_ready(job, chunk)["paths"]
        d = self.cfg.get("work_dir") or os.path.join(os.path.dirname(store_path(self.cfg)), "work")
        try:
            base, head = (CO.Checkout(os.path.join(d, job, n), kv["repo_url"], kv["base"]).ensure() for n in ("base", "head"))
            if (r := AP.apply(head, kv["patch:" + chunk], paths)) != "applied":
                return log("chunk %s: patch %s" % (chunk, r))
            if (r := TR.run(base, head, kv["test:" + chunk].split())["verdict"]) != "ok":
                return log("chunk %s: done-test %s" % (chunk, r))
            PB.publish(head, job, kv["title"], kv["base_branch"], self.open_pr, paths)
            self.st.set(job, "published:" + chunk, "1")
        except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as e:
            log("chunk %s: publish chain stopped: %s" % (chunk, type(e).__name__))

    def requeue(self, f):
        payload = {"job": f["job"], "stage": f["stage"], "chunk": f["chunk"]}
        st = self.st.get_all(f["job"]).get("payload:" + f["stage"])
        if st:
            payload = json.loads(st)
        if f["chunk"]:  # a chunk refire takes the ready path only: no queue row, the old attempt's lease is closed
            for l in self.st.open_leases():
                if l["job"] == f["job"] and l["chunk"] == f["chunk"] and l.get("attempt", 0) == f["refire"]:
                    self.st.close_lease(l["id"], "requeued", at=iso(self.clock()))
            self.st.bump_attempt(f["job"], f["chunk"])
            self.st.set_ready_state(f["job"], f["chunk"], "ready")
        else:
            self.st.enqueue(f["job"], f["stage"], f["chunk"], payload)

    def start_queued(self):
        busy = {f["job"] for f in self.st.pending() + self.st.running()}
        for q in self.st.queued(iso(self.clock())):
            job, stage = q["job"], q["stage"]
            if job in busy:
                continue
            ent = self.by_stage.get(stage)
            if not ent:
                log("no trigger for stage %s of job %s, dropped" % (stage, job))
                self.st.dequeue(q["id"])
                continue
            if L.may_fire(self.st.fire_count(job))[0] != "FIRE":
                log("job %s hit the fire cap, stage %s dropped" % (job, stage))
                self.st.dequeue(q["id"])
                continue
            if self.over_total(job):
                log("job %s is over its token total, stage %s dropped" % (job, stage))
                self.st.dequeue(q["id"])
                continue
            if L.packet_oversize(json.dumps(q["payload"]), self.cfg):
                log("job %s stage %s: packet over the cap, refused" % (job, stage))
                self.st.dequeue(q["id"])
                continue
            token = self.tokens.get("%s/%s" % (ent["agent"], ent["slug"]))
            if not token:
                log("no token for %s, skipped" % ent["slug"])
                continue
            self.st.set(job, "payload:" + stage, json.dumps(q["payload"]))
            fid = self.st.dequeue_to_intent(q["id"], job, q["chunk"], stage, ent.get("coworker", ""), ent["slug"])  # intent in, queue row out, before the fire
            busy.add(job)
            try:
                run_id, _ = T.fire(self.eng, ent["agent"], ent["slug"], token, q["payload"])
            except T.TriggerError as e:
                log("fire of %s failed (kept as intent, resolved next tick): %s" % (ent["slug"], e))
                continue
            self.st.fired(fid, run_id)
            log("fired stage %s of job %s: run %s" % (stage, job, run_id))

    def over_total(self, job):
        """True when the job's closed runs used job_token_cap tokens or more (key missing: no total cap)."""
        cap = L._pos(self.cfg.get("job_token_cap"))
        used = self.st.db.execute("SELECT COALESCE(SUM(tokens_in+tokens_out),0) FROM fires WHERE job=?", (job,)).fetchone()[0]
        return bool(cap) and used >= cap

    def lease_closed(self, f):
        """True when the fire's attempt (its refire number) has a lease for its chunk and none of that attempt is open."""
        ls = [l for l in self.st.db.execute("SELECT closed_at FROM leases WHERE job=? AND chunk=? AND attempt=?",
                                            (f["job"], f["chunk"], f["refire"]))] if f["chunk"] else []
        return bool(ls) and all(l[0] for l in ls)

    def sweep_leases(self):
        """Close an expired lease only after eng.cancel succeeded or the run row is terminal; a failed cancel keeps it open."""
        at = iso(self.clock())
        for l in self.st.open_leases():
            mine = lambda f: f["chunk"] == l["chunk"]
            if l["expires_at"] >= at or any(mine(f) for f in self.st.pending(l["job"])):
                continue
            try:
                for f in filter(mine, self.st.running(l["job"])):
                    row = T.read_run(self.eng, self._agent(f), f["run_id"])
                    if row and row.get("status") == "running":
                        self.eng.cancel(self._agent(f), f["run_id"])
                    self.st.close_run(f["run_id"], "cancelled", at, error="lease expired")
            except (E.EngineError, T.TriggerError) as e:
                log("lease %s kept open, cancel failed: %s" % (l["id"], e))
                continue
            self.st.close_lease(l["id"], "expired", at=at)

    def fire_reviews(self, job, pr, head, checks, owners):
        """Queue the review stage once per roster owner, only when every check at head is green; the wake claim
        (job-independent key: event, owner, head) lets a second look at the same head fire nothing."""
        if F.ci_state(checks) != "GREEN":
            return []
        new = [o for o in sorted(set(owners)) if wake.claim_wake(self.st, wake.review_event(pr), o, head)]
        for o in new:
            self.st.enqueue(job, "review", "", {"job": job, "stage": "review", "owner": o, "head": head})
        return new

    def after_reject(self, job, chunk, owners):
        """A REJECT of a chunk: limits.after_reject rules; ARBITER queues the arbiter stage, FIX queues nothing here."""
        what, why = L.after_reject(owners)
        if what == "ARBITER":
            self.st.enqueue(job, "arbiter", chunk, {"job": job, "stage": "arbiter", "chunk": chunk, "why": why})
        return what

    def fire_batch(self, batch):
        """One builder run for a picked batch (batch.pick_batch). Each chunk gets its own lease and attempt; all leases
        end together, 2 x run_limit_s from now (as start_ready). Returns the run id, None when no token."""
        ent = self.by_stage.get("build")
        token = ent and self.tokens.get("%s/%s" % (ent["agent"], ent["slug"]))
        if not token or not batch:
            return None
        job, ids = batch[0]["job"], [c["chunk"] for c in batch]
        exp = iso(self.clock() + 2 * self.cfg.get("run_limit_s", 600))
        payload = {"job": job, "stage": "build", "chunks": ids}
        fid = self.st.dequeue_to_intent(self.st.enqueue(job, "build", ids[0], payload), job, ids[0], "build",
                                        ent.get("coworker", ""), ent["slug"], batch[0]["paths"], exp)
        for c in batch[1:]:
            self.st.grant_lease(job, c["chunk"], c["paths"], exp, attempt=self.st.attempts(job, c["chunk"]))
        for c in ids:
            self.st.set_ready_state(job, c, "running")
        run_id, _ = T.fire(self.eng, ent["agent"], ent["slug"], token, payload)
        self.st.fired(fid, run_id)
        return run_id

    def start_ready(self):
        """Fire ready chunks (stage 'build') that readyq.eligible allows; running plain stages share the slot count."""
        ent = self.by_stage.get("build")
        fires = self.st.pending() + self.st.running()
        busy, stages = [(f["job"], f["chunk"]) for f in fires if f["chunk"]], sum(1 for f in fires if not f["chunk"])
        merged = {r[0] for r in self.st.db.execute("SELECT chunk FROM ready_chunks WHERE state='merged'")}
        token = ent and self.tokens.get("%s/%s" % (ent["agent"], ent["slug"]))
        for it in self.st.ready_list():
            if not token:
                return
            state = {"merged": merged, "busy": busy, "stages": stages, "leases": self.st.open_leases(),
                     "fired": self.st.fire_count(it["job"]), "cfg": self.cfg}
            if self.over_total(it["job"]) or not RQ.eligible(it, state)[0]:
                continue
            job, chunk = it["job"], it["chunk"]
            payload = {"job": job, "stage": "build", "chunk": chunk}
            q = self.st.enqueue(job, "build", chunk, payload)
            fid = self.st.dequeue_to_intent(q, job, chunk, "build", ent.get("coworker", ""), ent["slug"],
                                              it["paths"], iso(self.clock() + 2 * self.cfg.get("run_limit_s", 600)))
            self.st.set_ready_state(job, chunk, "running")
            busy.append((job, chunk))
            try:
                run_id, _ = T.fire(self.eng, ent["agent"], ent["slug"], token, payload)
            except T.TriggerError as e:
                log("fire of chunk %s failed (kept as intent): %s" % (chunk, e))
                continue
            self.st.fired(fid, run_id)
            log("fired chunk %s of job %s: run %s" % (chunk, job, run_id))

def build(cfg=None, eng=None, clock=time.time):
    cfg = load_runtime(cfg)
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
    sub.add_parser("setup")
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
        enqueue(inbox_path(cfg), a.job, a.stage, a.chunk, payload)
        print("queued %s %s" % (a.job, a.stage))
        return 0
    if a.cmd == "setup":
        try:
            for line in setup(E.Engine(), cfg):
                print(line)
        except (E.EngineError, T.TriggerError, RuntimeError, KeyError, OSError) as e:
            print("setup failed: %s" % ("unexpected engine answer" if isinstance(e, KeyError) else e), file=sys.stderr)
            return 1
        return 0
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    while True:
        try:
            r = build(cfg)
            break
        except NeedsSetup as e:
            if a.cmd == "once":
                print("runner: %s" % e, file=sys.stderr)
                return 1
            log("waiting for setup: %s" % e)  # stay up so `setup` can be exec'd in this container
            if stop.wait(10):
                return 0
        except (E.EngineError, T.TriggerError, RuntimeError) as e:
            print("runner: cannot start: %s" % e, file=sys.stderr)
            return 1
    if a.cmd == "once":
        r.tick()
        r.st.close()
        return 0
    run(r, stop, cfg.get("poll_s", POLL_S))
    r.st.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
