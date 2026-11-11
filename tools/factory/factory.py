#!/usr/bin/env python3
"""Factory scripts (Rob, 2026-11-10). One call replaces several tool calls.
Commands: packet, wt, pr-open, ci-wait, risk, merge-dev, job-open, release-pr, repo-check.
GitHub only through the gh/git wrappers; the token is never read or printed here."""
import json, os, re, subprocess, sys, time, shutil, urllib.request

GH, GIT = "/data/tools/bin/gh", "/data/tools/bin/git"
OWNERS = ("special-place-ai-heaven", "special-place-administrator")
WORK = os.environ.get("FACTORY_WORK", "/data/work")
REPOS, WT, STATE = WORK + "/repos", WORK + "/wt", WORK + "/state"
MAX_WORK_GB, MIN_FREE_GB, MAX_BUILDERS = 20, 30, 2
QUEUE_LIMIT_S, SLICE_S = 30 * 60, 450
PR_HEADS = ["## Done", "## Evidence", "## Not changed", "## Unsure", "## Open", "## Next owner and their done-test"]
WF = r"\.github/(workflows|actions)/|\.github/(CODEOWNERS|dependabot\.yml)$"
ISSUE_HEADS = ["## Goal", "## Done-test", "## Limits", "## Chunks"]
REL_HEADS = ["## What changed", "## How it was tested", "## CI status", "## Migration or config changes", "## Deploy notes"]
PR_TEMPLATE = """## Done
## Evidence
(commands run and their result)
## Not changed
(what a reviewer might expect, left alone on purpose)
## Unsure
## Open
## Next owner and their done-test
"""
ISSUE_TEMPLATE = """## Goal
## Done-test
## Limits
(what not to touch)
## Chunks
- [ ] 1. <result> | owner: <coworker> | done-test: <check> | depends on: -
## Memory hits
(EverOS, read once at plan time; "none" for a normal job)
## Token estimate
"""
REL_TEMPLATE = "\n".join(REL_HEADS) + "\n"


def die(msg, code=2):
    print("REFUSED: " + msg if code == 2 else msg)
    sys.exit(code)


def run(cmd, cwd="/tmp", check=True, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    if check and r.returncode:
        die("command failed: %s\n%s" % (" ".join(cmd[:6]), (r.stderr or r.stdout).strip()[-600:]), 1)
    return r


def api(path, *args, paginate=False):
    cmd = [GH, "api"] + (["--paginate"] if paginate else []) + [path] + list(args)
    r = run(cmd, check=False)
    if r.returncode:
        return None
    try:
        return json.loads(r.stdout)
    except Exception:
        # --paginate concatenates arrays
        try:
            return json.loads("[" + r.stdout.replace("][", "],[") + "]")[0] if r.stdout.strip() else None
        except Exception:
            return None


def repo_full(name):
    full = name if "/" in name else OWNERS[0] + "/" + name
    if full.split("/")[0] not in OWNERS:
        die("repo owner not allowed: " + full)
    return full


def short(full):
    return full.split("/")[1]


def trim(s, n):
    s = (s or "").replace("\r", "").strip()
    return s if len(s) <= n else s[:n] + "\n[... trimmed, %d more characters]" % (len(s) - n)


def checks(full, sha):
    d = api("repos/%s/commits/%s/check-runs?per_page=100" % (full, sha)) or {}
    out = []
    for c in d.get("check_runs", []):
        out.append({"name": c["name"], "status": c["status"], "conclusion": c.get("conclusion"), "id": c["id"],
                    "url": c.get("html_url", "")})
    return out


def ci_state(cs):
    """GREEN, RED, WAITING or NONE"""
    if not cs:
        return "NONE"
    bad = [c for c in cs if c["status"] == "completed" and c["conclusion"] in ("failure", "timed_out", "cancelled", "action_required", "startup_failure")]
    if any(c["conclusion"] in ("failure", "timed_out", "startup_failure") for c in bad):
        return "RED"
    if any(c["status"] != "completed" for c in cs):
        return "WAITING"
    return "RED" if bad else "GREEN"


def ci_table(cs):
    return "\n".join("  %-40s %-11s %s" % (c["name"][:40], c["status"], c["conclusion"] or "-") for c in sorted(cs, key=lambda c: c["name"])) or "  (no checks)"


# ---------- packet
def cmd_packet(a):
    if len(a) < 2:
        die("usage: packet <repo> <issue-or-PR number> [--full]")
    full, n, big = repo_full(a[0]), a[1].lstrip("#"), "--full" in a
    it = api("repos/%s/issues/%s" % (full, n))
    if not it:
        die("not found: %s#%s" % (full, n), 1)
    is_pr = "pull_request" in it
    print("# %s %s#%s: %s" % ("PR" if is_pr else "ISSUE", full, n, it["title"]))
    print("state: %s | labels: %s | author: %s | updated: %s" % (it["state"], ",".join(l["name"] for l in it["labels"]) or "-", it["user"]["login"], it["updated_at"]))
    print(it["html_url"])
    refs = sorted(set(re.findall(r"#(\d+)", it.get("body") or "")) - {n})
    if is_pr:
        pr = api("repos/%s/pulls/%s" % (full, n))
        print("base: %s <- head: %s @ %s | draft: %s | merged: %s | mergeable: %s | +%d -%d in %d files" % (
            pr["base"]["ref"], pr["head"]["ref"], pr["head"]["sha"][:8], pr["draft"], pr["merged"], pr.get("mergeable_state"),
            pr["additions"], pr["deletions"], pr["changed_files"]))
    print("linked: %s" % (", ".join("#" + r for r in refs) or "-"))
    print("\n## Body\n" + trim(it.get("body"), 6000 if big else 3000))
    if is_pr:
        cs = checks(full, pr["head"]["sha"])
        print("\n## CI: %s\n%s" % (ci_state(cs), ci_table(cs)))
        files = api("repos/%s/pulls/%s/files?per_page=100" % (full, n)) or []
        print("\n## Files")
        for f in files:
            print("  %-9s +%-4d -%-4d %s" % (f["status"], f["additions"], f["deletions"], f["filename"]))
        d = run([GH, "pr", "diff", n, "-R", full], check=False).stdout
        lines = d.splitlines()
        lim = 1500 if big else 400
        print("\n## Diff (%d lines%s)" % (len(lines), "" if len(lines) <= lim else ", first %d shown; --full shows 1500" % lim))
        print("\n".join(l[:300] for l in lines[:lim]))
    else:
        tl = api("repos/%s/issues/%s/timeline?per_page=100" % (full, n)) or []
        prs = sorted({str(e["source"]["issue"]["number"]) for e in tl if e.get("event") == "cross-referenced" and e.get("source", {}).get("issue", {}).get("pull_request")})
        print("\n## PRs that mention it: %s" % (", ".join("#" + p for p in prs) or "-"))
    cm = api("repos/%s/issues/%s/comments?per_page=100" % (full, n)) or []
    if is_pr:
        for r in api("repos/%s/pulls/%s/reviews?per_page=100" % (full, n)) or []:
            if r.get("body"):
                cm.append({"user": r["user"], "created_at": r.get("submitted_at") or "", "body": "[review %s] %s" % (r["state"], r["body"])})
    cm.sort(key=lambda c: c["created_at"])
    print("\n## Last comments (%d of %d)" % (min(5, len(cm)), len(cm)))
    for c in cm[-5:]:
        print("- %s %s: %s" % (c["created_at"], c["user"]["login"], trim(c["body"], 600).replace("\n", "\n  ")))


# ---------- wt
def du_gb(p):
    r = run(["du", "-sk", p], check=False)
    try:
        return int(r.stdout.split()[0]) / 1048576
    except Exception:
        return 0.0


def wt_dirs():
    out = []
    if os.path.isdir(WT):
        for r in sorted(os.listdir(WT)):
            for d in sorted(os.listdir(os.path.join(WT, r))):
                out.append((r, d, os.path.join(WT, r, d)))
    return out


def marker(repo, branch):
    return os.path.join(STATE, "green__%s__%s" % (repo, branch.replace("/", "_")))


def ensure_clone(full):
    p = os.path.join(REPOS, short(full))
    if not os.path.isdir(os.path.join(p, ".git")):
        run([GIT, "clone", "--quiet", "https://github.com/%s.git" % full, p], timeout=600)
    run([GIT, "fetch", "--quiet", "--prune", "origin"], cwd=p, timeout=300)
    return p


def remote_has(p, br):
    return run([GIT, "rev-parse", "--verify", "--quiet", "refs/remotes/origin/" + br], cwd=p, check=False).returncode == 0


def on_remote(p, sha):
    return bool(run([GIT, "for-each-ref", "--contains", sha, "refs/remotes/origin"], cwd=p).stdout.strip())


def wt_save(p, path, branch):
    """Die (nothing deleted) unless every commit of the worktree and its branch is on a remote branch.
    Unpushed commits go to rescue/<branch>-<sha8> first. Uncommitted changes refuse: pushing them could publish stray files."""
    if os.path.isdir(path) and run([GIT, "status", "--porcelain"], cwd=path).stdout.strip():
        die("%s has uncommitted changes. Commit and push them, or remove them yourself, then `wt done` again. Nothing deleted." % path)
    # --prune: a tracking ref of a branch deleted on GitHub must not count as proof
    if run([GIT, "fetch", "--quiet", "--prune", "origin"], cwd=p, check=False).returncode:
        die("cannot fetch origin, so cannot prove the commits of %s are saved. Nothing deleted." % branch)
    tips = {run([GIT, "rev-parse", "--verify", "--quiet", ref], cwd=c, check=False).stdout.strip()
            for c, ref in ((path, "HEAD"), (p, "refs/heads/" + branch)) if os.path.isdir(c)} - {""}
    for sha in sorted(tips):
        if on_remote(p, sha):
            continue
        rb = "rescue/%s-%s" % (branch, sha[:8])
        run([GIT, "push", "--quiet", "origin", "%s:refs/heads/%s" % (sha, rb)], cwd=p, check=False)
        if not on_remote(p, sha):
            die("%s has commits on no remote branch (%s) and the push to %s failed. Nothing deleted." % (branch, sha[:8], rb))
        print("RESCUED unpushed commits of %s to origin/%s" % (branch, rb))


def unlink_links(d):
    """Remove symlinks and junctions under d without entering them, so removing d cannot empty their targets."""
    for e in os.scandir(d):
        if e.is_symlink() or getattr(os.path, "isjunction", lambda _: False)(e.path):
            try:
                os.unlink(e.path)
            except OSError:
                os.rmdir(e.path)  # a directory symlink or junction on Windows
        elif e.is_dir():
            unlink_links(e.path)


def cmd_wt(a):
    if not a or a[0] not in ("new", "done", "list"):
        die("usage: wt new <repo> <issue> <chunk> [--base BRANCH] | wt done <repo> <issue> <chunk> | wt list")
    if a[0] == "list":
        act = 0
        for r, d, p in wt_dirs():
            br = run([GIT, "rev-parse", "--abbrev-ref", "HEAD"], cwd=p, check=False).stdout.strip()
            g = os.path.exists(marker(r, br))
            act += 0 if g else 1
            print("%s/%s  branch %s  %.2f GB  %s" % (r, d, br, du_gb(p), "CI green, waits for merge" if g else "ACTIVE builder"))
        st = shutil.disk_usage("/data")
        print("active builders: %d of %d | /data/work %.1f of %d GB | /data free %.0f GB (floor %d)" % (act, MAX_BUILDERS, du_gb(WORK), MAX_WORK_GB, st.free / 2**30, MIN_FREE_GB))
        return
    if len(a) < 4:
        die("usage: wt %s <repo> <issue> <chunk>" % a[0])
    full, issue, chunk = repo_full(a[1]), a[2].lstrip("#"), a[3]
    if not (issue.isdigit() and re.fullmatch(r"[a-z0-9]{1,12}", chunk)):
        die("issue must be a number and chunk a short id like 1 or 2b")
    repo = short(full)
    path = os.path.join(WT, repo, "%s-%s" % (issue, chunk))
    branch = "chunk/%s-%s" % (issue, chunk)
    if a[0] == "done":
        p = os.path.join(REPOS, repo)
        wt_save(p, path, branch)
        if os.path.isdir(path):
            unlink_links(path)
            # --force only because unlinking a committed symlink dirties the tree; wt_save proved the work is saved
            run([GIT, "worktree", "remove", "--force", path], cwd=p)
        run([GIT, "worktree", "prune"], cwd=p, check=False)
        run([GIT, "branch", "-D", branch], cwd=p, check=False)  # -D is safe: wt_save proved its commits are on a remote branch
        try:
            os.remove(marker(repo, branch))
        except OSError:
            pass
        print("removed worktree %s and local branch %s" % (path, branch))
        return
    if os.path.isdir(path):
        print("EXISTS %s (branch %s). Work there, or `wt done` first." % (path, branch))
        return
    st = shutil.disk_usage("/data")
    if st.free / 2**30 < MIN_FREE_GB:
        die("/data has %.0f GB free, floor is %d GB. Tell @boss." % (st.free / 2**30, MIN_FREE_GB))
    if du_gb(WORK) > MAX_WORK_GB:
        die("/data/work is over %d GB. Tell @boss; old worktrees need `wt done`." % MAX_WORK_GB)
    active = [(r, d) for r, d, p in wt_dirs() if not os.path.exists(marker(r, run([GIT, "rev-parse", "--abbrev-ref", "HEAD"], cwd=p, check=False).stdout.strip()))]
    if len(active) >= MAX_BUILDERS:
        die("%d builders are already active (%s). At most %d at once. Return BLOCKED to @boss." % (len(active), ", ".join("/".join(x) for x in active), MAX_BUILDERS))
    p = ensure_clone(full)
    info = api("repos/%s" % full)
    default = info["default_branch"]
    base = a[a.index("--base") + 1] if "--base" in a else ("dev" if remote_has(p, "dev") else "job/" + issue)
    if not remote_has(p, base):
        if base != "job/" + issue:
            die("base branch %s does not exist on origin" % base)
        run([GIT, "push", "--quiet", "origin", "refs/remotes/origin/%s:refs/heads/%s" % (default, base)], cwd=p)
        run([GIT, "fetch", "--quiet", "origin"], cwd=p)
        print("created job branch %s from %s" % (base, default))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    run([GIT, "worktree", "add", "--quiet", "-b", branch, path, "origin/" + base], cwd=p)
    run([GIT, "config", "branch.%s.factorybase" % branch, base], cwd=p)
    ex = os.path.join(p, ".git", "info", "exclude")
    if ".symforge" not in open(ex).read():
        open(ex, "a").write("\n.symforge/\n.symforge-knowledge.toml\n")
    notes = [f for f in ("AGENTS.md", "CLAUDE.md") if os.path.isfile(os.path.join(path, f))]
    print("WORKTREE %s\nbranch %s (from origin/%s, fresh)\nrepo %s | job issue #%s | chunk %s" % (path, branch, base, full, issue, chunk))
    print("build and test notes: %s" % (", ".join(notes) or "none in repo"))
    print("Next: edit here, quick checks only (lint, type check, named test files), commit, then `pr-open`.")


def wt_context():
    cwd = os.getcwd()
    if not cwd.startswith(WT + "/"):
        die("run this inside a worktree under %s (cd there in the same shell call)" % WT)
    top = run([GIT, "rev-parse", "--show-toplevel"], cwd=cwd).stdout.strip()
    repo = top[len(WT) + 1:].split("/")[0]
    branch = run([GIT, "rev-parse", "--abbrev-ref", "HEAD"], cwd=top).stdout.strip()
    base = run([GIT, "config", "branch.%s.factorybase" % branch], cwd=top, check=False).stdout.strip()
    m = re.fullmatch(r"chunk/(\d+)-([a-z0-9]+)", branch)
    if not m or not base:
        die("this worktree was not made by `wt new` (branch %s)" % branch)
    url = run([GIT, "remote", "get-url", "origin"], cwd=top).stdout.strip()
    full = repo_full(re.sub(r"\.git$", "", url.split("github.com/")[1]))
    return top, full, branch, base, m.group(1), m.group(2)


def has_heads(text, heads):
    return [h for h in heads if h not in text]


# ---------- pr-open
def cmd_pr_open(a):
    if "--template" in a:
        print(PR_TEMPLATE)
        return
    top, full, branch, base, issue, chunk = wt_context()
    if run([GIT, "status", "--porcelain"], cwd=top).stdout.strip():
        die("uncommitted changes. Commit everything for this chunk first (one push per chunk).")
    run([GIT, "fetch", "--quiet", "origin", base], cwd=top)
    ahead = run([GIT, "rev-list", "--count", "origin/%s..HEAD" % base], cwd=top).stdout.strip()
    if ahead == "0":
        die("no commits ahead of origin/%s" % base)
    changed = run([GIT, "diff", "--name-only", "origin/%s...HEAD" % base], cwd=top).stdout.split()
    if any(re.match(WF, f) for f in changed):
        die("this chunk changes workflow files (.github/workflows or actions). They are Rob's. Return BLOCKED to @boss.")
    msgs = run([GIT, "log", "--format=%B", "origin/%s..HEAD" % base], cwd=top).stdout
    if re.search(r"co-authored-by|generated with", msgs, re.I):
        die("a commit message has an AI trailer. Amend it before the push (nothing is pushed yet).")
    ex = json.loads(run([GH, "pr", "list", "-R", full, "--head", branch, "--state", "open", "--json", "number,url"]).stdout or "[]")
    if ex:
        if "--fix" not in a:
            die("PR already open: %s. To push a fix for red CI use `pr-open --fix`." % ex[0]["url"])
        run([GIT, "push", "--quiet", "origin", branch], cwd=top)
        try:
            os.remove(marker(short(full), branch))
        except OSError:
            pass
        print("PUSHED fix to %s\nPR %s\nNext: `ci-wait %s %s`" % (branch, ex[0]["url"], short(full), ex[0]["number"]))
        return
    if "--title" not in a or "--body-file" not in a:
        die("usage: pr-open --title 'T' --body-file FILE   (template: pr-open --template)")
    title, bf = a[a.index("--title") + 1], a[a.index("--body-file") + 1]
    body = open(bf).read()
    miss = has_heads(body, PR_HEADS)
    if miss:
        die("the handoff note lacks: %s. Template: pr-open --template" % ", ".join(miss))
    body = "Job: %s#%s, chunk %s\n\n%s" % (full, issue, chunk, body)
    tmp = os.path.join(STATE, "prbody-%d.md" % os.getpid())
    open(tmp, "w").write(body)
    run([GIT, "push", "--quiet", "-u", "origin", branch], cwd=top)
    r = run([GH, "pr", "create", "-R", full, "--base", base, "--head", branch, "--title", title, "--body-file", tmp])
    os.remove(tmp)
    url = r.stdout.strip().splitlines()[-1]
    print("PR %s\nbase %s <- %s | %s commits | %d files\nNext: `ci-wait %s %s`. Fix a red result yourself; hand over only when green." % (url, base, branch, ahead, len(changed), short(full), url.rsplit("/", 1)[-1]))


# ---------- ci-wait
def cmd_ci_wait(a):
    if len(a) < 2:
        die("usage: ci-wait <repo> <PR> [--once]")
    full, n = repo_full(a[0]), a[1].lstrip("#")
    pr = api("repos/%s/pulls/%s" % (full, n))
    if not pr:
        die("PR not found", 1)
    sha, branch = pr["head"]["sha"], pr["head"]["ref"]
    sf = os.path.join(STATE, "ciwait__%s__%s__%s.json" % (short(full), n, sha[:12]))
    try:
        first = json.load(open(sf))["first"]
    except Exception:
        first = time.time()
        json.dump({"first": first}, open(sf, "w"))
    end = time.time() + (0 if "--once" in a else SLICE_S)
    while True:
        cs = checks(full, sha)
        s = ci_state(cs)
        waited = time.time() - first
        if s in ("GREEN", "RED") or time.time() >= end or waited >= QUEUE_LIMIT_S:
            break
        time.sleep(20)
    print("CI %s | %s#%s @ %s | waited %d min in total" % (s, full, n, sha[:8], waited // 60))
    print(ci_table(cs))
    if s == "GREEN":
        open(marker(short(full), branch), "w").write(sha)
        print("NEXT: return the PR link to @boss. Do not merge.")
    elif s == "RED":
        for c in [c for c in cs if c["conclusion"] in ("failure", "timed_out", "startup_failure")][:2]:
            lg = run([GH, "api", "repos/%s/actions/jobs/%s/logs" % (full, c["id"])], check=False).stdout.splitlines()
            print("\n--- %s: last 60 log lines\n%s" % (c["name"], "\n".join(l[:240] for l in lg[-60:]) or "(no log; open %s)" % c["url"]))
        print("\nNEXT: fix it in your worktree, commit, `pr-open --fix`, then `ci-wait` again. Two red results on the same chunk: return BLOCKED to @boss.")
    elif waited >= QUEUE_LIMIT_S:
        print("STOP: 30 minutes without a result. Rob's runners are probably off. Return BLOCKED to @boss with this table. Do NOT push or re-run to wake it.")
    elif s == "NONE":
        print("NO CHECKS have started for this commit yet. Call `ci-wait` again (30-minute limit, %d min used). Do not push again." % (waited // 60))
    else:
        print("WAITING (queued is waiting, not failed). Call `ci-wait` again (30-minute limit, %d min used). Do not push again." % (waited // 60))


# ---------- risk
RULES = [
    ("STOP", r"^\.github/(workflows|actions)/|^\.github/(CODEOWNERS|dependabot\.yml)$", "workflow or GitHub settings file: Rob only"),
    ("BRUCE", r"auth|oidc|keycloak|login|session|token|secret|password|crypto|permission|guard|role|cors|csrf|sanitize|upload", "auth, secrets or trust boundary"),
    ("BRUCE", r"(^|/)(package(-lock)?\.json|pnpm-lock\.yaml|yarn\.lock|Cargo\.(toml|lock)|requirements[^/]*\.txt|pyproject\.toml|Dockerfile[^/]*|docker-compose[^/]*\.yml)$", "dependencies or image"),
    ("CODD", r"migration|schema|\.sql$|\.entity\.ts$|prisma|typeorm|seed", "schema, migration or data"),
    ("GRACE", r"openapi|swagger|\.controller\.ts$|\.dto\.ts$|\.proto$|/api/|contract", "API contract"),
    ("DIETER", r"\.(scss|css|html|svg)$|theme|design-tokens", "visible UI"),
    ("FRED", r"^frontend/.*\.(ts|tsx|html|scss|css)$", "frontend behaviour: browser check of the touched flow"),
]
SAFE = r"\.(md|txt)$|(^|/)(docs?|specs?|tasks|\.planning)/|\.spec\.ts$|\.test\.[jt]sx?$|(^|/)tests?/|__tests__"


def cmd_risk(a):
    if len(a) < 2:
        die("usage: risk <repo> <PR> [--no-jev]")
    full, n = repo_full(a[0]), a[1].lstrip("#")
    pr = api("repos/%s/pulls/%s" % (full, n))
    files = api("repos/%s/pulls/%s/files?per_page=100" % (full, n)) or []
    need, plain = {}, []
    for f in files:
        fn, hit = f["filename"], False
        test_only = re.search(r"\.spec\.ts$|\.test\.[jt]sx?$|(^|/)tests?/|__tests__|\.md$", fn)
        for who, pat, why in RULES:
            if re.search(pat, fn, re.I) and not (test_only and who not in ("STOP",)):
                need.setdefault(who, [why, []])[1].append(fn)
                hit = True
        if not hit and not re.search(SAFE, fn, re.I):
            plain.append(fn)
    tops = {f["filename"].split("/")[0] for f in files}
    lines = sum(f["additions"] + f["deletions"] for f in files)
    if len(files) > 25 or lines > 1200:
        need.setdefault("ADA", ["large change (%d files, %d lines): structure check" % (len(files), lines), []])
    print("RISK %s#%s: %d files, %d lines, top folders: %s" % (full, n, len(files), lines, ", ".join(sorted(tops))))
    if "STOP" in need:
        print("STOP: touches %s. Workflow files are Rob's. Return BLOCKED to Rob." % ", ".join(need["STOP"][1][:5]))
    jev_note = ""
    if plain and not need and "--no-jev" not in a and (lines > 150 or len(plain) > 6):
        jev_note = jev_risk(pr["title"], [f["filename"] for f in files], need)
    extra = [w for w in need if w != "STOP"]
    for w in extra:
        print("EXTRA REVIEWER %s: %s%s" % (w, need[w][0], (" (" + ", ".join(need[w][1][:4]) + (" ..." if len(need[w][1]) > 4 else "") + ")") if need[w][1] else ""))
    if not extra and "STOP" not in need:
        print("EXTRA REVIEWERS: none. LINUS alone.")
    if jev_note:
        print(jev_note)


def jev_risk(title, files, need):
    key = None
    try:
        for l in open("@@JEV_KEYFILE@@"):
            if l.startswith("TYPESAFE_API_KEY="):
                key = l.split("=", 1)[1].strip().strip("\"'")
    except Exception:
        pass
    if not key:
        return "Jev: not asked (no key)."
    crit = {"true": "Yes, this change plausibly does that", "false": "No, nothing in the title or file names suggests it"}
    qs = {"BRUCE": "Does the change in `change` touch authentication, permissions, secrets, input from outside or dependencies?",
          "CODD": "Does the change in `change` alter a database schema, a migration or stored data?",
          "GRACE": "Does the change in `change` alter an API that another program or the frontend calls?",
          "FRED": "Does the change in `change` alter what a user sees or does in the browser?"}
    body = json.dumps({"model": "jev-latest", "state": {"change": {"title": title, "files": files[:60]}},
                       "questions": {k: {"type": "noul", "instructions": v, "criteria": crit} for k, v in qs.items()}}).encode()
    try:
        req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=body, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "rerun-factory-risk/0.1"})
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.load(r)
        res = {k: round(out["answers"][k]["noul"], 2) for k in qs}
        for k, v in res.items():
            if v >= 0.7:
                need.setdefault(k, ["Jev says likely (%.2f), file names alone were unclear" % v, []])
        return "Jev (unclear case, file names and title only, %s input tokens): %s" % (out.get("usage", {}).get("input_tokens", "?"), res)
    except Exception as e:
        return "Jev: call failed (%s); decided on the path table alone." % str(e)[:80]


# ---------- merge-dev
def cmd_merge_dev(a):
    if len(a) < 2:
        die("usage: merge-dev <repo> <PR> [--note 'one-line verdict, posted on the PR']")
    full, n = repo_full(a[0]), a[1].lstrip("#")
    pr = api("repos/%s/pulls/%s" % (full, n))
    info = api("repos/%s" % full)
    if not pr:
        die("PR not found", 1)
    base, head = pr["base"]["ref"], pr["head"]["ref"]
    if base in ("main", "master", info["default_branch"]) and base != "dev":
        die("base is %s. Merging into main is Rob's step. Give your verdict to @boss instead." % base)
    if not (base == "dev" or base.startswith("job/")):
        die("base %s is neither dev nor a job branch" % base)
    if pr["state"] != "open" or pr["draft"]:
        die("PR is %s%s" % (pr["state"], " (draft)" if pr["draft"] else ""))
    files = api("repos/%s/pulls/%s/files?per_page=100" % (full, n)) or []
    if any(re.match(WF, f["filename"]) for f in files):
        die("PR changes workflow files. Rob only.")
    cs = checks(full, pr["head"]["sha"])
    s = ci_state(cs)
    if s != "GREEN":
        die("CI is %s on %s, not GREEN. Reviewers never wait on CI: return BLOCKED to @boss.\n%s" % (s, pr["head"]["sha"][:8], ci_table(cs)))
    if "--note" in a:
        run([GH, "pr", "comment", n, "-R", full, "--body", "Review ACCEPT @%s: %s" % (pr["head"]["sha"][:8], a[a.index("--note") + 1][:1500])], check=False)
    r = run([GH, "pr", "merge", n, "-R", full, "--merge", "--match-head-commit", pr["head"]["sha"]], check=False)
    if r.returncode:
        die("merge failed: %s" % (r.stderr or r.stdout).strip()[-400:], 1)
    run([GH, "api", "-X", "DELETE", "repos/%s/git/refs/heads/%s" % (full, head)], check=False)
    m = api("repos/%s/pulls/%s" % (full, n))
    print("MERGED %s#%s into %s as %s | head %s | remote branch %s deleted" % (full, n, base, (m.get("merge_commit_sha") or "?")[:8], pr["head"]["sha"][:8], head))
    mm = re.fullmatch(r"chunk/(\d+)-([a-z0-9]+)", head)
    if mm and os.path.isdir(os.path.join(WT, short(full), "%s-%s" % mm.groups())):
        try:
            cmd_wt(["done", full, mm.group(1), mm.group(2)])
        except SystemExit:
            print("KEPT worktree %s/%s-%s: the merge stands, clean the worktree up and run `wt done` again." % (short(full), mm.group(1), mm.group(2)))


# ---------- job-open / release-pr
def cmd_job_open(a):
    if "--template" in a:
        print(ISSUE_TEMPLATE)
        return
    if len(a) < 1 or "--title" not in a or "--body-file" not in a:
        die("usage: job-open <repo> --title 'T' --body-file FILE   (template: job-open --template)")
    full = repo_full(a[0])
    body = open(a[a.index("--body-file") + 1]).read()
    miss = has_heads(body, ISSUE_HEADS)
    if miss:
        die("the work order lacks: %s. Template: job-open --template" % ", ".join(miss))
    r = run([GH, "issue", "create", "-R", full, "--title", a[a.index("--title") + 1], "--body-file", a[a.index("--body-file") + 1]])
    url = r.stdout.strip().splitlines()[-1]
    print("JOB %s\nStart every dispatch for it with: JOB %s#%s" % (url, short(full), url.rsplit("/", 1)[-1]))


def cmd_release_pr(a):
    if "--template" in a:
        print(REL_TEMPLATE)
        return
    if len(a) < 2 or "--title" not in a or "--body-file" not in a:
        die("usage: release-pr <repo> <head branch: dev or job/N> --title 'T' --body-file FILE   (template: release-pr --template)")
    full, head = repo_full(a[0]), a[1]
    if not (head == "dev" or head.startswith("job/")):
        die("head must be dev or a job branch")
    info = api("repos/%s" % full)
    body = open(a[a.index("--body-file") + 1]).read()
    miss = has_heads(body, REL_HEADS)
    if miss:
        die("the release note lacks: %s. Template: release-pr --template" % ", ".join(miss))
    merged = json.loads(run([GH, "pr", "list", "-R", full, "--base", head, "--state", "merged", "--limit", "50", "--json", "number,title,mergedAt"]).stdout or "[]")
    if head.startswith("job/"):
        body = "Closes #%s\n\n%s" % (head.split("/")[1], body)
    body += "\n## Chunks merged into `%s`\n" % head + ("\n".join("- #%d %s" % (p["number"], p["title"]) for p in merged[:30]) or "- (none found)") + "\n"
    tmp = os.path.join(STATE, "relbody-%d.md" % os.getpid())
    open(tmp, "w").write(body)
    r = run([GH, "pr", "create", "-R", full, "--base", info["default_branch"], "--head", head, "--title", a[a.index("--title") + 1], "--body-file", tmp])
    os.remove(tmp)
    print("RELEASE PR %s\ninto %s, merging is Rob's step. After Rob says \"merged\", @boss saves the EverOS release entry." % (r.stdout.strip().splitlines()[-1], info["default_branch"]))


# ---------- repo-check
def cmd_repo_check(a):
    if not a:
        die("usage: repo-check <repo>")
    full = repo_full(a[0])
    info = api("repos/%s" % full)
    if not info:
        die("repo not found or no access", 1)
    d = info["default_branch"]
    dev = api("repos/%s/branches/dev" % full) is not None
    print("REPO %s | default %s | dev branch: %s | private: %s" % (full, d, "yes" if dev else "no (use job/<issue>)", info["private"]))
    for f in ("AGENTS.md", "CLAUDE.md"):
        print("%s: %s" % (f, "yes" if api("repos/%s/contents/%s" % (full, f)) else "no"))
    wfs = api("repos/%s/contents/.github/workflows" % full) or []
    pr_wf = 0
    for w in wfs:
        r = run([GH, "api", "repos/%s/contents/.github/workflows/%s" % (full, w["name"]), "-H", "Accept: application/vnd.github.raw"], check=False).stdout
        head = r.split("\njobs:")[0]
        on_pr = bool(re.search(r"pull_request", head))
        tests = bool(re.search(r"\b(test|jest|vitest|pytest|cargo test|nextest|playwright)\b", r, re.I))
        pr_wf += 1 if (on_pr and tests) else 0
        bl = re.search(r"pull_request:\s*\n\s+branches:\s*(.+)", head)
        print("workflow %-28s on PRs: %-3s runs tests: %-3s %s" % (w["name"], "yes" if on_pr else "no", "yes" if tests else "no", ("PR base filter: " + bl.group(1)) if bl else ""))
    print("CI THAT RUNS TESTS ON PRs: %s" % ("YES" if pr_wf else "NO. Tell Rob before building here."))
    prs = api("repos/%s/pulls?state=all&per_page=1" % full) or []
    if prs:
        cs = checks(full, prs[0]["head"]["sha"])
        print("latest PR #%d (%s): CI %s\n%s" % (prs[0]["number"], prs[0]["state"], ci_state(cs), ci_table(cs)))
    rs = api("repos/%s/rulesets" % full) or []
    print("rulesets: %s" % (", ".join("%s (%s)" % (r["name"], r["enforcement"]) for r in rs) or "none"))


CMDS = {"packet": cmd_packet, "wt": cmd_wt, "pr-open": cmd_pr_open, "ci-wait": cmd_ci_wait, "risk": cmd_risk,
        "merge-dev": cmd_merge_dev, "job-open": cmd_job_open, "release-pr": cmd_release_pr, "repo-check": cmd_repo_check}

if __name__ == "__main__":
    name = os.environ.get("FACTORY_CMD") or (sys.argv[1] if len(sys.argv) > 1 else "")
    args = sys.argv[1:] if os.environ.get("FACTORY_CMD") else sys.argv[2:]
    if name not in CMDS:
        die("commands: " + ", ".join(CMDS))
    os.makedirs(STATE, exist_ok=True)
    CMDS[name](args)
