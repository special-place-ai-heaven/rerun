"""The hold on all sending, kept in the ledger so it survives a restart.

One kv row per kind: job "-", key "hold:<kind>", value JSON {"until": epoch seconds}.
"""
import json

# The engine's own probe time is PLAN_LIMIT_PROBE_MS in
# apps/engine/src/connections/plan-limits.ts (#198, Settled 7). Taken from the
# code, not from runs: no run read on 2026-11-13 shows a spent plan.
PLAN_LIMIT_HOLD_S = 30 * 60

KINDS = ("plan limit", "sign-in renewal")

_JOB = "-"
_PREFIX = "hold:"


def arm(st, kind, until):
    """Hold sending of this kind until `until`; a second call replaces the time."""
    st.set(_JOB, _PREFIX + kind, json.dumps({"until": until}))


def clear(st, kind):
    """End the hold of this kind (the ledger has no kv delete, so until becomes 0)."""
    arm(st, kind, 0)


def active(st, now):
    """The first held kind (KINDS order, then others) whose until is later than now, else None.

    A hold whose time has passed is not active: the first send after it is the probe.
    """
    rows = {}
    for k, v in st.get_all(_JOB).items():
        if not k.startswith(_PREFIX):
            continue
        try:
            rows[k[len(_PREFIX):]] = json.loads(v)["until"]
        except (ValueError, KeyError, TypeError):
            continue
    order = [k for k in KINDS if k in rows] + sorted(k for k in rows if k not in KINDS)
    for kind in order:
        if rows[kind] > now:
            return {"kind": kind, "until": rows[kind]}
    return None
