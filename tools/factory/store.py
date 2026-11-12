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
CREATE TABLE IF NOT EXISTS leases(
  id INTEGER PRIMARY KEY AUTOINCREMENT, job TEXT NOT NULL, chunk TEXT NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 0, paths TEXT NOT NULL DEFAULT '[]',
  granted_at TEXT NOT NULL, expires_at TEXT NOT NULL, closed_at TEXT, reason TEXT);
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
        have = {r[1] for r in self.db.execute("PRAGMA table_info(fires)")}
        for col in ("cache_read", "cache_write", "seconds"):  # old databases: add the cost columns
            if col not in have:
                self.db.execute(f"ALTER TABLE fires ADD COLUMN {col} INTEGER")

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

    def close_run(self, run_id, status, at=None, tokens_in=0, tokens_out=0, error=None,
                  cache_read=None, cache_write=None):
        """Close a run and write its cost: tokens (cache columns stay NULL when the run row has none) and seconds."""
        at = at or now()
        self.db.execute("UPDATE fires SET status=?, ended_at=?, tokens_in=?, tokens_out=?, error=?, cache_read=?, "
                        "cache_write=?, seconds=MAX(0, CAST(strftime('%s', ?) AS INTEGER) - CAST(strftime('%s', intent_at) AS INTEGER)) "
                        "WHERE run_id=?", (status, at, tokens_in, tokens_out, error, cache_read, cache_write, at, run_id))

    def stage_cost(self, run_id):
        """The cost row of one run: tokens in/out/cache and seconds (None when the run is unknown)."""
        r = self.db.execute("SELECT job,chunk,stage,status,tokens_in,tokens_out,cache_read,cache_write,seconds "
                            "FROM fires WHERE run_id=?", (run_id,)).fetchone()
        return dict(r) if r else None

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

    def grant_lease(self, job, chunk, paths, expires_at, attempt=0, at=None):
        """Open a lease on a chunk's paths until expires_at (ISO). Returns the lease id."""
        cur = self.db.execute("INSERT INTO leases(job,chunk,attempt,paths,granted_at,expires_at) VALUES(?,?,?,?,?,?)",
                              (job, chunk, attempt, json.dumps(list(paths)), at or now(), expires_at))
        return cur.lastrowid

    def _lease(self, r):
        r = dict(r)
        r["paths"] = json.loads(r["paths"])
        return r

    def get_lease(self, lease_id):
        r = self.db.execute("SELECT * FROM leases WHERE id=?", (lease_id,)).fetchone()
        return self._lease(r) if r else None

    def open_leases(self):
        return [self._lease(r) for r in self.db.execute("SELECT * FROM leases WHERE closed_at IS NULL ORDER BY id")]

    def close_lease(self, lease_id, reason, at=None):
        """Close with a reason; a lease that is already closed keeps its first reason."""
        self.db.execute("UPDATE leases SET closed_at=?, reason=? WHERE id=? AND closed_at IS NULL",
                        (at or now(), reason, lease_id))

    def expire_leases(self, at):
        """Close every open lease whose expires_at is before `at`; returns the leases closed."""
        out = [l for l in self.open_leases() if l["expires_at"] < at]
        for l in out:
            self.close_lease(l["id"], "expired", at=at)
        return out

    def _rows(self, where, job):
        sql = "SELECT * FROM fires WHERE " + where + (" AND job=?" if job is not None else "") + " ORDER BY id"
        return [dict(r) for r in self.db.execute(sql, (job,) if job is not None else ())]
