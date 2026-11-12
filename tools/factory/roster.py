"""Roster: coworkers, areas, required reviewers and builders, read from roster.json.

Pure functions, no network. `load(text)` validates and returns a roster; the other
functions take that roster as first argument.
"""
import json
import re

CLASSES = ("rule", "plan", "build", "advise", "gate", "watch")
LEVELS = ("writer", "reviewer", "issues", "none")
EXEMPT = ("tests", "docs")   # these areas stand in for the file; only sensitive areas still apply
STACK = "stack"              # builder value: "next matching area"
GATE_SENSITIVE = "BRUCE"


def glob_re(glob):
    """Glob to regex, case-insensitive, whole path. `**/` = 0+ dirs, `**` = anything, `*` = no '/', `?` = one char."""
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out), re.I)


def _bad(msg):
    raise ValueError("roster: " + msg)


def load(text):
    try:
        data = json.loads(text)
    except ValueError as e:
        _bad("not JSON (%s)" % e)
    cw = data.get("coworkers") if isinstance(data, dict) else None
    if not isinstance(cw, dict) or not cw:
        _bad("coworkers missing")
    for h, row in cw.items():
        if not isinstance(row, dict) or h != h.lower():
            _bad("coworker %r: handle must be lowercase with a row" % h)
        for f in ("class", "github", "wake"):
            if f not in row:
                _bad("coworker %s: field %s missing" % (h, f))
        if row["class"] not in CLASSES:
            _bad("coworker %s: unknown class %r" % (h, row["class"]))
        if row["github"] not in LEVELS:
            _bad("coworker %s: unknown github level %r" % (h, row["github"]))
        if not isinstance(row["wake"], list) or not all(isinstance(w, str) for w in row["wake"]):
            _bad("coworker %s: wake must be a list of strings" % h)

    def owner_ok(who, where):
        if who not in cw or cw[who]["github"] not in ("writer", "reviewer"):
            _bad("%s: owner %r is not a coworker who can write or review" % (where, who))

    def builder_ok(who, where, allow_stack):
        if who == STACK and allow_stack:
            return
        if who not in cw or cw[who]["github"] != "writer":
            _bad("%s: builder %r is not a coworker with github writer" % (where, who))

    default = data.get("default")
    if not isinstance(default, dict) or "owner" not in default or "builder" not in default:
        _bad("default needs owner and builder")
    owner_ok(default["owner"], "default")
    builder_ok(default["builder"], "default", False)
    areas, seen = [], set()
    for a in data.get("areas") or []:
        name = a.get("name") if isinstance(a, dict) else None
        if not name or name in seen or name == "default":
            _bad("area name missing, repeated or reserved: %r" % name)
        seen.add(name)
        globs = a.get("globs")
        if not isinstance(globs, list) or not globs or not all(isinstance(g, str) for g in globs):
            _bad("area %s: globs must be a non-empty list" % name)
        owner_ok(a.get("owner"), "area " + name)
        builder_ok(a.get("builder"), "area " + name, True)
        areas.append({"name": name, "owner": a["owner"], "builder": a["builder"],
                      "sensitive": bool(a.get("sensitive")), "globs": globs,
                      "res": [glob_re(g) for g in globs]})
    return {"coworkers": cw, "areas": areas,
            "default": {"name": "default", "owner": default["owner"], "builder": default["builder"],
                        "sensitive": False, "globs": [], "res": []}}


def _matches(roster, path):
    return [a for a in roster["areas"] if any(r.fullmatch(path) for r in a["res"])]


def _touched(roster, path):
    """Areas a file touches. tests/docs files match only those, plus any sensitive area (never dropped)."""
    hit = _matches(roster, path)
    if any(a["name"] in EXEMPT for a in hit):
        return [a for a in hit if a["name"] in EXEMPT or a["sensitive"]]
    return hit or [roster["default"]]


def areas(roster, files):
    """{area name: [files]} in table order (default last)."""
    got = {}
    for f in files:
        for a in _touched(roster, f):
            got.setdefault(a["name"], []).append(f)
    order = [a["name"] for a in roster["areas"]] + ["default"]
    return {n: got[n] for n in order if n in got}


def required(roster, files, builder=None):
    """UPPERCASE reviewer names: owner of each touched area (the chunk builder is replaced by the default owner), plus BRUCE on a sensitive area."""
    by_name = {a["name"]: a for a in roster["areas"] + [roster["default"]]}
    need, builder = set(), (builder or "").lower()
    for name in areas(roster, files):
        a = by_name[name]
        who = a["owner"]
        if who == builder:
            who = roster["default"]["owner"]
        need.add(who.upper())
        if a["sensitive"]:
            need.add(GATE_SENSITIVE)
    return need


def builder(roster, paths):
    """Lowercase handle of the coworker who builds a chunk with these paths; raises when paths need two builders."""
    paths = list(paths)
    if not paths:
        return roster["default"]["builder"]
    plain = [p for p in paths if not any(a["name"] in EXEMPT for a in _matches(roster, p))]
    picked = {}
    for p in plain or paths:
        who = roster["default"]["builder"]
        for a in _matches(roster, p):
            if a["builder"] != STACK:
                who = a["builder"]
                break
        picked.setdefault(who, []).append(p)
    if len(picked) > 1:
        raise ValueError("split the chunk: " + "; ".join("%s: %s" % (w, ", ".join(ps[:3])) for w, ps in sorted(picked.items())))
    return next(iter(picked))
