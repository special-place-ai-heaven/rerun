"""Counters and limits of the factory runner (rerun#53 chunk 3, Settled 3). Pure functions: plain counters and
timestamps in, an (action, reason) pair out. The runner keeps the counters in the ledger and acts on the action:
FIX (fire a fix build or fix round, counter +1), PLAN (back to Plan with the reason, plan_round +1), BLOCKED,
NEEDS_BOSS (BLOCKED plus label needs-boss), BUILD, FIRE, REFIRE, RUN, WAIT, FAILED (one failed attempt), OK."""
import datetime, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ledger as L

FIX_BUILDS, JOB_FIXES, REVIEW_ROUNDS, PLAN_ROUNDS = 2, 2, 2, 3
FIRED_CAP = 20
RUN_LIMIT_S, CI_START_LIMIT_S = 45 * 60, 30 * 60
STALL_S = 10 * 60
PENDING_TICKS, RESTART_REFIRES = 3, 1
RESTARTED = "interrupted: engine restarted"


def ts(iso):
    """Epoch seconds of an ISO time. The engine writes '...11.123Z', GitHub and the ledger '...11Z': as text '.' sorts
    before 'Z', so compare these only through ts()."""
    return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def replan(plan_round, reason):
    if plan_round >= PLAN_ROUNDS:
        return "BLOCKED", "plan_round %d/%d used, the next plan would be round %d: %s" % (plan_round, PLAN_ROUNDS, plan_round + 1, reason)
    return "PLAN", reason


def fix_or_replan(used, cap, plan_round, reason):
    """After a failure: a fix while used < cap (chunk fix builds, job CI fixes, review rounds: cap 2 each), else re-plan.
    The first build is not a fix: with cap 2 the third failure re-plans."""
    if used < cap:
        return "FIX", reason
    return replan(plan_round, "failed after %d/%d fixes: %s" % (used, cap, reason))


def challenge(verdict, rejects_in_row, plan_round, text):
    """verdict READY or REJECT; rejects_in_row counts the PLAN REJECTs right before this one."""
    if verdict == "READY":
        return "BUILD", None
    if rejects_in_row >= 1:
        return "NEEDS_BOSS", "second PLAN REJECT in a row: " + text
    return replan(plan_round, text)


def may_fire(fired_total):
    """Checked before the pre-fire intent is written: a job never fires more than FIRED_CAP runs."""
    if fired_total >= FIRED_CAP:
        return "BLOCKED", "fired %d/%d runs for this job, the safety cap" % (fired_total, FIRED_CAP)
    return "FIRE", None


STANDARD_CHUNK_CAP, BUILDER_CAPACITY, PER_JOB_CAP = 400000, 3, 2


def _pos(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None


def chunk_cap(cfg=None, entry=None, lane=None):
    """Per-chunk token cap: the strictest of the standard chunk, the global, the entry and the lane value."""
    vals = [_pos(v) for v in (STANDARD_CHUNK_CAP, (cfg or {}).get("token_cap"), (entry or {}).get("token_cap"), lane)]
    return min(v for v in vals if v is not None)


def batch_cap(cfg, chunks, entry=None, lane=None):
    """A batch run's cap: chunks x the per-chunk cap."""
    return chunks * chunk_cap(cfg, entry, lane)


def stage_cfg(cfg, entry=None):
    """cfg with the per-stage overrides of a runner.json trigger entry (keys run_limit_s, stall_s, token_cap) laid over
    the global ones. token_cap is the strictest of the two: an entry cannot raise the global. A stage that must end
    fast (the R2 proof stage) carries its own short run_limit_s."""
    out = dict(cfg or {})
    for k in ("run_limit_s", "stall_s", "token_cap"):
        if entry and k in entry:
            out[k] = min(entry[k], out[k]) if k == "token_cap" and _pos(out.get(k)) and _pos(entry[k]) else entry[k]
    return out



def run_limits(cfg=None):
    """Run limits from the runner.json keys run_limit_s, stall_s, token_cap (seconds, seconds, tokens), with defaults.
    A missing, null or non-positive stall_s or token_cap switches that rule off."""
    cfg = cfg or {}
    def num(key, default):
        v = cfg.get(key, default)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else None
    return {"run_limit_s": num("run_limit_s", RUN_LIMIT_S) or RUN_LIMIT_S, "stall_s": num("stall_s", STALL_S), "token_cap": num("token_cap", None)}

def run_outcome(row, now, steps=None, cfg=None):
    """A runs row (trigger.read_run) -> RUNNING, CANCEL (a running run over its wall time, stalled or over its token
    cap: the caller cancels it through engine.py), DONE, RESTARTED, REFIRE_ONCE (error row: fired again once, the store
    counts refires), FAILED or MISSING. steps is {"last_step_at": ISO or None, "tokens": int} (optional), cfg the
    runner.json dict (optional). now is epoch seconds. Pure: no I/O."""
    if not row or not row.get("status"):
        return "MISSING", "run not found in system.db"
    st, rid = row["status"], row.get("id")
    if st == "running":
        lim, steps = run_limits(cfg), steps or {}
        started = ts(row["started_at"])
        if now - started > lim["run_limit_s"]:
            return "CANCEL", "run %s still running after %d s (limit %d s)" % (rid, now - started, lim["run_limit_s"])
        if lim["token_cap"] is not None and (steps.get("tokens") or 0) > lim["token_cap"]:
            return "CANCEL", "run %s used %d tokens (cap %d)" % (rid, steps["tokens"], lim["token_cap"])
        if steps and lim["stall_s"] is not None:
            last = ts(steps["last_step_at"]) if steps.get("last_step_at") else started
            if now - last > lim["stall_s"]:
                return "CANCEL", "run %s stalled: no new step for %d s (limit %d s)" % (rid, now - last, lim["stall_s"])
        return "RUNNING", None
    if st == "done":
        return "DONE", None
    if st == "error":
        if RESTARTED in (row.get("error") or ""):
            return "RESTARTED", None
        return "REFIRE_ONCE", "run %s ended error: %s" % (rid, (row.get("error") or "-")[:200])
    return "FAILED", "run %s ended %s: %s" % (rid, st, (row.get("error") or "-")[:200])


def restart(refires):
    """A run that ended with an engine restart is fired again once per stage, not counted as a fix."""
    if refires < RESTART_REFIRES:
        return "REFIRE", None
    return "FAILED", "run interrupted by an engine restart again after %d refire" % refires


def ci_overdue(dispatched, now):
    """A CI run not started CI_START_LIMIT_S after its dispatch (ISO) makes the job BLOCKED."""
    return now - ts(dispatched) > CI_START_LIMIT_S


def resolve_pending(firing, slug, rows, now, tick_seconds):
    """A firing written before its POST but with no run id: the earliest runs row with this trigger_slug started at or
    after the firing is its run. None after PENDING_TICKS ticks: FAILED, one attempt. Never fired again."""
    f = ts(firing)
    mine = sorted((ts(r["started_at"]), r["id"]) for r in rows if r.get("trigger_slug") == slug and r.get("started_at") and ts(r["started_at"]) >= f)
    if mine:
        return "RUN", mine[0][1]
    if now - f >= PENDING_TICKS * tick_seconds:
        return "FAILED", "firing of %s at %s has no run after %d ticks" % (slug, firing, PENDING_TICKS)
    return "WAIT", None


def keeps_merged(old_text, new_text, merged):
    """A re-plan keeps every MERGED chunk: same id, same line (the checkbox aside). old_text is the accepted plan."""
    def by_id(text):
        return {L.chunk(l)["id"]: l.strip()[6:].strip() for l in L.chunk_lines(text)}
    old, new = by_id(old_text), by_id(new_text)
    bad = sorted(i for i in merged if old.get(i) is None or new.get(i) != old.get(i))
    return ("BLOCKED", "re-plan changes merged chunk(s): " + ", ".join(bad)) if bad else ("OK", None)
