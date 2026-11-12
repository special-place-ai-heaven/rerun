"""store.py: the runner's ledger in SQLite (WAL). One writer: an exclusive flock on <db>.lock.
An intent row is written and committed BEFORE a stage is fired; fired() adds the run id after.
A crash in between leaves an intent with no run id: pending() lists it, the caller decides
(resolve it against the engine, or refire once: refire count). No network, no engine key here."""
import fcntl, json, os, sqlite3, time

SCHEMA = """
CREATE TABLE IF NOT EXISTS fires(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job TEXT NOT NULL, chunk TEXT NOT NULL DEFAULT '', stage TEXT NOT NULL,
  coworker TEXT NOT NULL DEFAULT '', slug TEXT NOT NULL DEFAULT '',
  intent_at TEXT NOT NULL, run_id TEXT, status TEXT NOT NULL DEFAULT 'intent',
  ended_at TEXT, tokens_in INTEGER NOT NULL DEFAULT 0, tokens_out INTEGER NOT NULL DEFAULT 0,
  error TEXT, refire INTEGER NOT NULL DEFAULT 0);
CREATE UNIQUE INDEX IF NOT EXISTS fires_run ON fires(run_id) WHERE run_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS kv(job TEXT NOT NULL, k TEXT NOT NULL, v TEXT NOT NULL, PRIMARY KEY(job, k));
CREATE TABLE IF NOT EXISTS queue(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job TEXT NOT NULL, stage TEXT NOT NULL, chunk TEXT NOT NULL DEFAULT '',
  payload TEXT NOT NULL, enqueued_at TEXT NOT NULL, not_before TEXT);
CREATE TABLE IF NOT EXISTS ready_chunks(
  job TEXT NOT NULL, chunk TEXT NOT NULL, builder TEXT NOT NULL DEFAULT '',
  paths TEXT NOT NULL DEFAULT '[]', deps TEXT NOT NULL DEFAULT '[]',
  state TEXT NOT NULL DEFAULT 'ready', attempts INTEGER NOT NULL DEFAULT 0,
  added_at TEXT NOT NULL, PRIMARY KEY(job, chunk));
"""
OPEN = ("intent", "running")


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Store:
    def __init__(self, path):
        self.path = path
        self._lock = open(path + ".lock", "a")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lock.close()
            raise RuntimeError("store is locked by another writer")
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.close()
        self._lock.close()  # releases the flock

    def intent(self, job, chunk, stage, coworker="", slug="", at=None):
        """Record that a stage is about to fire. Committed before the caller fires. Returns the fire id.
        refire = number of earlier fires of the same job/chunk/stage."""
        n = self.db.execute("SELECT COUNT(*) FROM fires WHERE job=? AND chunk=? AND stage=?",
                            (job, chunk, stage)).fetchone()[0]
        cur = self.db.execute(
            "INSERT INTO fires(job,chunk,stage,coworker,slug,intent_at,refire) VALUES(?,?,?,?,?,?,?)",
            (job, chunk, stage, coworker, slug, at or now(), n))
        return cur.lastrowid

    def fired(self, fire_id, run_id):
        self.db.execute("UPDATE fires SET run_id=?, status='running' WHERE id=? AND status='intent'",
                        (run_id, fire_id))

    def close_run(self, run_id, status, at=None, tokens_in=0, tokens_out=0, error=None):
        self.db.execute("UPDATE fires SET status=?, ended_at=?, tokens_in=?, tokens_out=?, error=? WHERE run_id=?",
                        (status, at or now(), tokens_in, tokens_out, error, run_id))

    def abandon(self, fire_id, error="no run id after intent", at=None):
        """Resolve a pending intent that never fired (decided by the caller)."""
        self.db.execute("UPDATE fires SET status='lost', ended_at=?, error=? WHERE id=? AND run_id IS NULL",
                        (at or now(), error, fire_id))

    def pending(self, job=None):
        """Intents with no run id: a crash happened between intent and fire (or the fire is in flight)."""
        return self._rows("status='intent'", job)

    def running(self, job=None):
        return self._rows("status='running'", job)

    def refires(self, job, chunk, stage):
        """Number of fires beyond the first for this stage (0 = fired once or never)."""
        n = self.db.execute("SELECT COUNT(*) FROM fires WHERE job=? AND chunk=? AND stage=?",
                            (job, chunk, stage)).fetchone()[0]
        return max(0, n - 1)

    def resume(self, job):
        """What a restarted runner needs: pending intents, running runs, last fire, saved kv."""
        last = self.db.execute("SELECT * FROM fires WHERE job=? ORDER BY id DESC LIMIT 1", (job,)).fetchone()
        return {"pending": self.pending(job), "running": self.running(job),
                "last": dict(last) if last else None, "state": self.get_all(job)}

    def foreign(self, engine_run_ids):
        """R6: engine run ids that this store never recorded as a stage fire. Empty list = pass."""
        ids = list(engine_run_ids)
        if not ids:
            return []
        q = ",".join("?" * len(ids))
        known = {r[0] for r in self.db.execute(f"SELECT run_id FROM fires WHERE run_id IN ({q})", ids)}
        return [i for i in ids if i not in known]

    def set(self, job, k, v):
        self.db.execute("INSERT INTO kv VALUES(?,?,?) ON CONFLICT(job,k) DO UPDATE SET v=excluded.v", (job, k, str(v)))

    def get_all(self, job):
        return {r["k"]: r["v"] for r in self.db.execute("SELECT k,v FROM kv WHERE job=?", (job,))}

    def enqueue(self, job, stage, chunk="", payload=None, not_before=None, at=None):
        """Queue a stage (the runner's own table). payload is a dict (default {job, stage, chunk}); not_before an ISO time
        before which the row is not offered by queued(). Returns the queue id."""
        payload = payload or {"job": job, "stage": stage, "chunk": chunk}
        cur = self.db.execute("INSERT INTO queue(job,stage,chunk,payload,enqueued_at,not_before) VALUES(?,?,?,?,?,?)",
                              (job, stage, chunk, json.dumps(payload), at or now(), not_before))
        return cur.lastrowid

    def queued(self, at=None):
        """Queue rows in id order, payload decoded. With `at` (ISO), rows whose not_before is later are left out."""
        rows = []
        for r in self.db.execute("SELECT * FROM queue ORDER BY id"):
            r = dict(r)
            if at is not None and r["not_before"] and r["not_before"] > at:
                continue
            r["payload"] = json.loads(r["payload"])
            rows.append(r)
        return rows

    def dequeue(self, queue_id):
        self.db.execute("DELETE FROM queue WHERE id=?", (queue_id,))

    def fire_count(self, job):
        """Number of fires ever recorded for the job (the fired-runs safety cap counts these)."""
        return self.db.execute("SELECT COUNT(*) FROM fires WHERE job=?", (job,)).fetchone()[0]

    def known_run_ids(self):
        return {r[0] for r in self.db.execute("SELECT run_id FROM fires WHERE run_id IS NOT NULL")}

    def dequeue_to_intent(self, queue_id, job, chunk, stage, coworker="", slug=""):
        """One commit: the intent row in, the queue row out. Committed before the caller fires. Returns the fire id."""
        self.db.execute("BEGIN IMMEDIATE")
        try:
            fid = self.intent(job, chunk, stage, coworker, slug)
            self.dequeue(queue_id)
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise
        return fid

    def add_ready(self, job, chunk, paths=(), builder="", deps=(), at=None):
        """Ready-chunk queue: add a chunk (idempotent per job/chunk)."""
        self.db.execute("INSERT OR IGNORE INTO ready_chunks(job,chunk,builder,paths,deps,added_at) VALUES(?,?,?,?,?,?)",
                        (job, chunk, builder, json.dumps(list(paths)), json.dumps(list(deps)), at or now()))

    def _ready(self, r):
        r = dict(r)
        r["paths"], r["deps"] = json.loads(r["paths"]), json.loads(r["deps"])
        return r

    def get_ready(self, job, chunk):
        r = self.db.execute("SELECT * FROM ready_chunks WHERE job=? AND chunk=?", (job, chunk)).fetchone()
        return self._ready(r) if r else None

    def ready_list(self, job=None):
        """Chunks in state 'ready', oldest first."""
        sql = "SELECT * FROM ready_chunks WHERE state='ready'" + (" AND job=?" if job is not None else "") + " ORDER BY rowid"
        return [self._ready(r) for r in self.db.execute(sql, (job,) if job is not None else ())]

    def set_ready_state(self, job, chunk, state):
        self.db.execute("UPDATE ready_chunks SET state=? WHERE job=? AND chunk=?", (state, job, chunk))

    def attempts(self, job, chunk):
        r = self.db.execute("SELECT attempts FROM ready_chunks WHERE job=? AND chunk=?", (job, chunk)).fetchone()
        return r[0] if r else 0

    def bump_attempt(self, job, chunk):
        self.db.execute("UPDATE ready_chunks SET attempts=attempts+1 WHERE job=? AND chunk=?", (job, chunk))
        return self.attempts(job, chunk)

    def _rows(self, where, job):
        sql = "SELECT * FROM fires WHERE " + where + (" AND job=?" if job is not None else "") + " ORDER BY id"
        return [dict(r) for r in self.db.execute(sql, (job,) if job is not None else ())]
