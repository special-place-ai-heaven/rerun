"""Run clocks and retry class (rerun#207, phase A of #198). Pure: no network, no ledger write. It decides nothing that
limits.run_outcome decides: it builds that function's inputs and maps its answer to a retry class."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import limits as L

RETRY_BACKOFF_S = (60, 120, 240)
_ERR = ("provider_overloaded", "429", "rate limit", "sign-in renewed during the run", "403 attention required")
_ROOM = ("builders are already active", "GB free, floor is", "of memory available, floor is", "/data/work is over")


def seen_after(run, prev, now_iso):
    """Last sighting of a run's step count: `at` moves only when run["steps"] differs from prev; the first sighting
    uses run["startedAt"] (get_run carries no time of the last step)."""
    steps = run["steps"]
    if prev is None:
        return {"steps": steps, "at": run["startedAt"]}
    if prev["steps"] != steps:
        return {"steps": steps, "at": now_iso}
    return {"steps": prev["steps"], "at": prev["at"]}


def outcome(run, seen, now, cfg=None):
    """limits.run_outcome for a get_run record; now is epoch seconds. run None gives MISSING."""
    if run is None:
        return L.run_outcome(None, now, None, cfg)
    if cfg is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner.json")) as f:
            cfg = json.load(f)
    row = {"id": run["runId"], "status": run["status"], "started_at": run["startedAt"], "error": run.get("error")}
    steps = {"last_step_at": (seen or {}).get("at"), "tokens": run.get("totalTokens") or 0}
    return L.run_outcome(row, now, steps, cfg)


def klass(kind, run=None, blocked=None):
    """transient, cancel, work, plan, or None (DONE/RUNNING)."""
    if kind in ("DONE", "RUNNING"):
        return None
    if kind in ("RESTARTED", "MISSING"):
        return "transient"
    if kind == "CANCEL":
        return "cancel"
    if kind == "BLOCKED":
        text = (blocked or "").strip()
        if text.upper().startswith("BLOCKED:"):
            text = text[8:].strip()
        if any(p in text for p in _ROOM):
            return "transient"
        if text.lower().startswith("plan:"):
            return "plan"
        return "work"
    err = ((run or {}).get("error") or "").lower()
    if any(p in err for p in _ERR):
        return "transient"
    return "work"


def backoff(n):
    """Seconds before the n-th transient retry (1-based); None from the 4th."""
    return RETRY_BACKOFF_S[n - 1] if 1 <= n <= len(RETRY_BACKOFF_S) else None
