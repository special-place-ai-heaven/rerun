"""publish.py: commit the worktree, push factory/job-<issue> to origin, open the pull request (rerun#71 C6e).
open_pr(title, head, base, body) is passed in; this module reads no token and knows no GitHub."""
import subprocess


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _outside(worktree, paths):
    ok = tuple(p.rstrip("/") for p in paths)
    changed = [l.split(None, 1)[1] for l in _git(worktree, "status", "--porcelain", "-uall").splitlines()]
    return [c for c in changed if not any(c == p or c.startswith(p + "/") for p in ok)]


def publish(worktree, issue, title, base, open_pr, paths, remote="origin", body=""):
    """Commit only `paths` on factory/job-<issue>, push it, call open_pr. A changed or new file outside
    `paths` raises ValueError before anything is committed or pushed. Returns the pushed commit sha."""
    head = "factory/job-%s" % issue
    extra = _outside(worktree, paths)
    if extra:
        raise ValueError("files outside the chunk paths: %s" % ", ".join(extra))
    _git(worktree, "checkout", "-q", "-B", head)
    _git(worktree, "add", "--", *paths)
    if _git(worktree, "diff", "--cached", "--name-only"):
        _git(worktree, "commit", "-qm", title)
    _git(worktree, "push", "-q", remote, "%s:refs/heads/%s" % (head, head))
    open_pr(title, head, base, body) if body else open_pr(title, head, base)
    return _git(worktree, "rev-parse", "HEAD")
