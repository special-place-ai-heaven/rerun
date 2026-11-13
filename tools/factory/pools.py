"""Worker types read from the dispatch settings. Pure: no network, no ledger."""


def _coworkers(items):
    return [{"id": c["id"], "name": c["name"], "runs": c.get("runs", 1)} for c in items]


def types(cfg):
    """{type: {"coworkers": [{"id", "name", "runs"}], "max_jobs": int or None}}."""
    if "types" in cfg:
        return {t: {"coworkers": _coworkers(v.get("coworkers", [])),
                    "max_jobs": v.get("max_jobs")}
                for t, v in cfg["types"].items()}
    return {
        "coder": {"coworkers": _coworkers(cfg.get("builders", [])),
                  "max_jobs": cfg.get("max_jobs", 8)},
        "reviewer": {"coworkers": _coworkers(cfg.get("reviewers", [])),
                     "max_jobs": None},
    }


def names(cfg):
    return {c["id"]: c["name"] for t in types(cfg).values() for c in t["coworkers"]}


def pick(cfg, worker, busy):
    """First coworker id of the type not in busy; None if all busy or type unknown."""
    t = types(cfg).get(worker)
    if t is None:
        return None
    return next((c["id"] for c in t["coworkers"] if c["id"] not in busy), None)


def max_jobs(cfg, worker):
    t = types(cfg).get(worker)
    return None if t is None else t["max_jobs"]
