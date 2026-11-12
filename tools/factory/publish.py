"""publish.py: commit the worktree, push factory/job-<issue> to origin, open the pull request (rerun#71 C6e).
open_pr(title, head, base) is passed in; this module reads no token and knows no GitHub."""
import subprocess


def _git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def publish(worktree, issue, title, base, open_pr, remote="origin"):
    """Commit all changes on factory/job-<issue>, push it, call open_pr. Returns the pushed commit sha."""
    head = "factory/job-%s" % issue
    _git(worktree, "checkout", "-q", "-B", head)
    _git(worktree, "add", "-A")
    if _git(worktree, "status", "--porcelain"):
        _git(worktree, "commit", "-qm", title)
    _git(worktree, "push", "-q", remote, "%s:refs/heads/%s" % (head, head))
    open_pr(title, head, base)
    return _git(worktree, "rev-parse", "HEAD")
