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


def run_outcome(row, now):
    """A runs row (trigger.read_run) -> RUNNING, OVERDUE (BLOCKED: never fired again, never cancelled), DONE, RESTARTED,
    FAILED or MISSING. now is epoch seconds."""
    if not row or not row.get("status"):
        return "MISSING", "run not found in system.db"
    st, rid = row["status"], row.get("id")
    if st == "running":
        if now - ts(row["started_at"]) > RUN_LIMIT_S:
            return "OVERDUE", ("run %s still running after %d min. Run %s may still be running and burning tokens: stop it in the UI."
                               % (rid, RUN_LIMIT_S // 60, rid))
        return "RUNNING", None
    if st == "done":
        return "DONE", None
    if st == "error" and RESTARTED in (row.get("error") or ""):
        return "RESTARTED", None
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
