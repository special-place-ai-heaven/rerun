#!/usr/bin/env python3
"""Chunk proof gate (chunk A of factory-tooling). Reads evidence from GitHub itself; every receipt is bound
to the PR's current head SHA. Exit 0 PASS, 3 FAIL, 1 could not answer (API error is never PASS).
Commands: gate <repo> <PR>   |   review <repo> <PR> ACCEPT|REJECT --as NAME --note 'text'"""
import fnmatch, json, os, re, subprocess, sys
sys.path.insert(0, "/data/tools/factory")
import factory as F

GH = F.GH
TESTF = r"\.spec\.[jt]sx?$|\.test\.[jt]sx?$|(^|/)tests?/.*\.(ts|tsx|js|jsx|rs|py)$|__tests__/.*\.(ts|tsx|js|jsx)$|_test\.(py|go)$"
REVIEW_RE = re.compile(r"^\s*Review (ACCEPT|REJECT) @([0-9a-f]{8}): ([A-Za-z][A-Za-z0-9_-]*) (ACCEPT|REJECT)\b")
ANSI = re.compile(r"(?:\x1b|\^\[)\[[0-9;]*m")  # real ESC, or the caret form (^[) some log paths show


class NoAnswer(Exception):
    pass


def gh_json(path, paginate=False, jq=".[]"):
    """Raises NoAnswer on any API error. paginate=True returns the flat list of items (jq picks them per page)."""
    cmd = [GH, "api"] + (["--paginate", "--jq", jq] if paginate else []) + [path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode:
        raise NoAnswer("API error on %s: %s" % (path, (r.stderr or r.stdout).strip()[-200:]))
    t = r.stdout.strip()
    if paginate:
        return [json.loads(l) for l in t.splitlines() if l.strip()]
    return json.loads(t) if t else []


def head_checks(full, sha):
    out = []
    for c in gh_json("repos/%s/commits/%s/check-runs?per_page=100" % (full, sha), paginate=True, jq=".check_runs[]"):
        out.append({"name": c["name"], "status": c["status"], "conclusion": c.get("conclusion"), "id": c["id"], "url": c.get("html_url", "")})
    return out


_logs = {}


def job_log(full, url):
    m = re.search(r"/actions/runs/(\d+)/job/(\d+)", url)
    if not m:
        raise NoAnswer("check has no job url: %s" % url)
    if m.group(2) not in _logs:
        r = subprocess.run([GH, "run", "view", m.group(1), "-R", full, "--log", "--job", m.group(2)], capture_output=True, text=True, timeout=300)
        if r.returncode or not r.stdout.strip():
            raise NoAnswer("job log unavailable (expired?) %s: %s" % (url, r.stderr.strip()[-150:]))
        _logs[m.group(2)] = ANSI.sub("", r.stdout)
    return _logs[m.group(2)]


def results(log):
    """[(kind, name, ok, line)] from jest PASS/FAIL lines, cargo nextest PASS/FAIL lines and cargo 'test x ... ok'."""
    out = []
    binary = None  # cargo test: current integration binary (tests/<stem>.rs), so names read '<stem>::test'
    for ln in log.splitlines():
        r = re.search(r"Z\s+Running (unittests )?(\S+?)\.rs \(", ln)
        if r:
            binary = None if r.group(1) else os.path.basename(r.group(2))
            continue
        m = re.search(r"Z\s+(PASS|FAIL|SIGABRT|SIGSEGV|TIMEOUT|LEAK-FAIL)\s+\[\s*[\d.]+s\]\s+(?:\(\s*\d+/\d+\)\s+)?(\S+)\s+(\S+)\s*$", ln)
        if m:  # cargo nextest: 'PASS [ 0.072s] ( 1/1666) crate::bin test_name' -> name 'crate::bin::test_name'
            out.append(("nextest-it" if "::" in m.group(2) else "nextest-unit", m.group(2) + "::" + m.group(3), m.group(1) == "PASS", ln.split("Z ", 1)[1].strip()[:120]))
            continue
        m = re.search(r"Z (PASS|FAIL) (\S+)", ln)
        if m:
            out.append(("jest", m.group(2), m.group(1) == "PASS", ln.split("Z ", 1)[1][:120]))
            continue
        m = re.search(r"Z test (\S+) \.\.\. (ok|FAILED)\b", ln)
        if m:
            nm = m.group(1) if binary is None else binary + "::" + m.group(1)
            out.append(("cargo-unit" if binary is None else "cargo-it", nm, m.group(2) == "ok", ln.split("Z ", 1)[1][:120]))
    return out


def _norm(x):
    return x[2:] if x.startswith("./") else x


def same(a, b):
    """DONE_TEST names: equal, or one ends with '::' + the other. Never last-segment-only."""
    a, b = _norm(a), _norm(b)
    if a == b or a.endswith("::" + b) or b.endswith("::" + a):
        return True
    # file paths: jest logs print package-relative paths; match on a "/" boundary, the shorter side must itself contain "/"
    return ("/" in b and a.endswith("/" + b)) or ("/" in a and b.endswith("/" + a))


def rust_prefix(path):
    """('bin', stem) for crates/x/tests/<stem>.rs; ('mod', 'a::b') for crates/x/src/a/b.rs (inline #[cfg(test)] mod tests); else None."""
    parts = _norm(path).split("/")
    if not parts[-1].endswith(".rs"):
        return None
    if len(parts) >= 2 and parts[-2] == "tests":
        return ("bin", parts[-1][:-3])
    if "src" in parts:
        mods = parts[len(parts) - 1 - parts[::-1].index("src") + 1:]
        mods[-1] = mods[-1][:-3]
        if mods[-1] in ("mod", "lib", "main"):
            mods = mods[:-1]
        return ("mod", "::".join(mods))
    return None


def test_hit(tf, name, kind=""):
    """Does test result `name` (of `kind` from results()) belong to changed test file `tf`? Rust integration file
    tests/<stem>.rs: only an integration-binary result of binary <stem>. Rust src/<mod>.rs: only a unit result under
    '<mod>::tests::' right after the crate prefix (nextest-unit 'crate::<mod>::tests::t', cargo-unit '<mod>::tests::t').
    Everything else (jest): same()."""
    rp = rust_prefix(tf)
    if not rp:
        return same(name, tf)
    segs = name.split("::")
    if rp[0] == "bin":
        return (kind == "nextest-it" and len(segs) >= 3 and segs[1] == rp[1]) or (kind == "cargo-it" and len(segs) >= 2 and segs[0] == rp[1])
    want = [x for x in rp[1].split("::") if x] + ["tests"]
    if kind == "nextest-unit":
        segs = segs[1:]
    elif kind != "cargo-unit":
        return False
    return segs[:len(want)] == want and len(segs) > len(want)


def inline_rust_test(f):
    """Only ADDED patch lines count (context, removed lines and @@ headers do not)."""
    return bool(re.search(r"(^|/)src/.*\.rs$", f["filename"]) and re.search(r"(?m)^\+(?!\+\+).*(#\[(\w+::)?test\]|cfg\(test\)|mod tests)", f.get("patch") or ""))


def clean_glob(g):
    g = g.strip(" `")
    if g.endswith("."):
        g = g[:-1]
    return g.strip(" `")


def parse_issue(full, jobrepo, jobn, chunk):
    body = gh_json("repos/%s/issues/%s" % (F.repo_full(jobrepo), jobn)).get("body") or ""
    line = next((l for l in body.splitlines() if re.match(r"\s*- \[.\] %s\." % re.escape(chunk), l, re.I)), None)
    if not line:
        return None, body, {}
    f = {}
    for part in line.split("|")[1:]:
        k, _, v = part.strip().partition(":")
        f[k.strip().lower()] = v.strip()
    return line, body, f


def gate(repo, n):
    full = F.repo_full(repo)
    pr = gh_json("repos/%s/pulls/%s" % (full, n))
    head = pr["head"]["sha"]
    s8 = head[:8]
    files = gh_json("repos/%s/pulls/%s/files?per_page=100" % (full, n), paginate=True)
    lines = sum(f["additions"] + f["deletions"] for f in files)
    pbody = pr.get("body") or ""
    res = {}

    def put(cid, ok, receipt):
        res[cid] = {"ok": bool(ok), "receipt": receipt, "sha": head}

    # chunk id and work order
    m = re.search(r"Job: ([\w./-]+)#(\d+), chunk (\w+)", pbody)
    mb = re.fullmatch(r"chunk/(\d+)-(\w+)", pr["head"]["ref"])
    jobrepo, jobn, chunk = (m.group(1), m.group(2), m.group(3)) if m else ((full, mb.group(1), mb.group(2)) if mb else (full, None, None))
    idconf = None
    if m and mb and (mb.group(1) != m.group(2) or mb.group(2).lower() != m.group(3).lower()):
        idconf = "PR body says %s#%s chunk %s but branch %s says issue %s chunk %s" % (m.group(1), m.group(2), m.group(3), pr["head"]["ref"], mb.group(1), mb.group(2))
    line, ibody, fld = (None, "", {})
    if jobn:
        line, ibody, fld = parse_issue(full, jobrepo, jobn, chunk)

    # 1 CI_GREEN
    cs = head_checks(full, head)
    if not cs and not gh_json("repos/%s/commits/%s" % (full, head)):
        raise NoAnswer("cannot read checks")
    st = F.ci_state(cs)
    put("CI_GREEN", st == "GREEN", "%s: %d check-runs on %s, e.g. %s" % (st, len(cs), s8, cs[0]["url"] if cs else "none"))

    # 2 DONE_TEST
    dt = fld.get("done-test")
    if idconf:
        put("DONE_TEST", False, "chunk id mismatch: " + idconf)
    elif not dt:
        put("DONE_TEST", False, "no done-test in work order %s#%s chunk %s" % (jobrepo, jobn, chunk) if jobn else "chunk id not found (branch chunk/<issue>-<cN> or 'Job: <repo>#<n>, chunk <cN>')")
    else:
        seen = None
        for c in cs:
            if c["conclusion"] != "success":
                continue
            for k, name, ok, ln in results(job_log(full, c["url"])):
                if same(name, dt):
                    if not ok:
                        seen = (False, c["url"], ln)
                        break
                    seen = seen if seen and not seen[0] else (True, c["url"], ln)
            if seen and not seen[0]:
                break
        if seen and seen[0]:
            put("DONE_TEST", True, "%s | %s" % (seen[2], seen[1]))
        elif seen:
            put("DONE_TEST", False, "failed on head: %s | %s" % (seen[2], seen[1]))
        else:
            put("DONE_TEST", False, "'%s' not found as passed in any job log on %s" % (dt, s8))

    # 3 FAIL_BEFORE
    tfiles = [f["filename"] for f in files if f["status"] in ("added", "modified") and (re.search(TESTF, f["filename"]) or inline_rust_test(f))]
    commits = [c["sha"] for c in gh_json("repos/%s/pulls/%s/commits?per_page=100" % (full, n), paginate=True) if c["sha"] != head]
    if not tfiles:
        put("FAIL_BEFORE", False, "PR touches no test file: nothing that failed before")
    else:
        missing, rec = [], []
        red = []
        for sha in commits:
            for c in head_checks(full, sha):
                if c["conclusion"] == "failure":
                    red.append((sha, c))
        for tf in tfiles:
            hit = None
            for sha, c in red:
                for k, name, ok, ln in results(job_log(full, c["url"])):
                    if not ok and test_hit(tf, name, k):
                        hit = "%s FAILED on %s | %s" % (ln, sha[:8], c["url"])
                        break
                if hit:
                    break
            (rec if hit else missing).append(hit or tf)
        put("FAIL_BEFORE", not missing, ("; ".join(rec)) if not missing else "no failing log on an older commit for: " + ", ".join(missing))

    # 4 REVIEWS
    need, stop = {"LINUS"}, []
    for f in files:
        fn = f["filename"]
        test_only = re.search(r"\.spec\.ts$|\.test\.[jt]sx?$|(^|/)tests?/|__tests__|\.md$", fn)
        for who, pat, why in F.RULES:
            if re.search(pat, fn, re.I) and not (test_only and who != "STOP"):
                if who == "STOP":
                    stop.append(fn)
                else:
                    need.add(who)
    if len(files) > 25 or lines > 1200:
        need.add("ADA")
    verdict = {}
    for cm in sorted(gh_json("repos/%s/issues/%s/comments?per_page=100" % (full, n), paginate=True), key=lambda c: c["created_at"]):
        mm = REVIEW_RE.match(cm.get("body") or "")
        if mm and mm.group(2) == s8:
            verdict[mm.group(3).upper()] = (mm.group(4), cm["html_url"])
    bad = sorted(w for w in need if verdict.get(w, ("", ""))[0] != "ACCEPT")
    if stop:
        put("REVIEWS", False, "STOP: workflow or GitHub settings file touched (Rob only): " + ", ".join(stop[:3]))
    else:
      put("REVIEWS", not bad, ("%s ACCEPT @%s | %s" % (", ".join(sorted(need)), s8, " ".join(verdict[w][1] for w in sorted(need)))) if not bad else
        "need ACCEPT @%s from: %s (have: %s)" % (s8, ", ".join(bad), ", ".join("%s %s" % (k, v[0]) for k, v in verdict.items()) or "none on this head"))

    # 5 LIMITS
    mx = int(re.sub(r"\D", "", fld.get("max-lines", "")) or 800)
    wf = [f["filename"] for f in files if re.search(F.WF, f["filename"])]
    globs = []
    in_lim = False
    for l in ibody.splitlines():
        if l.startswith("## "):
            in_lim = l.strip() == "## Limits"
        if in_lim and "do not touch:" in l.lower():
            globs += [clean_glob(g) for g in re.split(r"do not touch:", l, flags=re.I)[1].split(",") if clean_glob(g)]
    dnt = [f["filename"] for f in files if any(fnmatch.fnmatch(f["filename"], g) for g in globs)]
    why = []
    if lines > mx:
        why.append("%d changed lines > max %d" % (lines, mx))
    if wf:
        why.append("workflow files: " + ", ".join(wf[:3]))
    if dnt:
        why.append("do-not-touch: " + ", ".join(dnt[:3]))
    put("LIMITS", not why, "; ".join(why) or "%d lines <= %d, %d files, no workflow file, %d do-not-touch globs" % (lines, mx, len(files), len(globs)))

    # 6 HANDOFF
    miss = F.has_heads(pbody, F.PR_HEADS)
    put("HANDOFF", not miss, "missing sections: " + ", ".join(miss) if miss else "all %d PR_HEADS sections present in PR body" % len(F.PR_HEADS))

    failed = [k for k, v in res.items() if not v["ok"]]
    head_line = "GATE %s %s#%s @%s%s" % ("FAIL" if failed else "PASS", F.short(full), n, s8, (": " + ", ".join(failed)) if failed else "")
    print(head_line)
    for k, v in res.items():
        print("%s %s %s" % (k, "PASS" if v["ok"] else "FAIL", v["receipt"]))
    os.makedirs("/data/work/state/gate", exist_ok=True)
    json.dump({"repo": full, "pr": int(n), "head": head, "verdict": "FAIL" if failed else "PASS", "checks": res},
              open("/data/work/state/gate/%s-%s-%s.json" % (F.short(full), n, head), "w"), indent=1)
    return 3 if failed else 0


def review(a):
    if len(a) < 3 or a[2] not in ("ACCEPT", "REJECT") or "--as" not in a or "--note" not in a:
        print("usage: review <repo> <PR> ACCEPT|REJECT --as <NAME> --note '<text>'")
        return 2
    full, n = F.repo_full(a[0]), a[1].lstrip("#")
    name = a[a.index("--as") + 1].upper()
    note = a[a.index("--note") + 1][:1500]
    if not re.fullmatch(r"[A-Z][A-Z0-9_-]*", name):
        print("--as must be a name like LINUS, BRUCE")
        return 2
    pr = gh_json("repos/%s/pulls/%s" % (full, n))
    s8 = pr["head"]["sha"][:8]
    body = "Review %s @%s: %s %s @%s: %s" % (a[2], s8, name, a[2], s8, note)
    r = subprocess.run([GH, "pr", "comment", n, "-R", full, "--body", body], capture_output=True, text=True)
    if r.returncode:
        print("review not posted: " + (r.stderr or r.stdout)[-200:])
        return 1
    print("POSTED " + body[:160] + " | " + r.stdout.strip())
    return 0


if __name__ == "__main__":
    cmd = os.environ.get("GATE_CMD", "gate")
    a = sys.argv[1:]
    try:
        if cmd == "review":
            sys.exit(review(a))
        if len(a) < 2:
            print("usage: gate <repo> <PR>")
            sys.exit(2)
        sys.exit(gate(a[0], a[1].lstrip("#")))
    except NoAnswer as e:
        print("GATE UNKNOWN: could not answer: %s" % e)
        sys.exit(1)
    except SystemExit:
        raise
    except Exception as e:
        print("GATE UNKNOWN: could not answer: %r" % e)
        sys.exit(1)
