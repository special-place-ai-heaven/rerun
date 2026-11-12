"""Re-review packet (rerun#71 O6): what a reviewer sees after a REJECT is the diff from the rejected commit to head;
the full diff against base when the rejected commit is not an ancestor of head (history was rewritten)."""
import subprocess


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def review_diff(repo, base, head, rejected=None):
    """Diff text for the reviewer: rejected..head when rejected is an ancestor of head, else base..head."""
    if rejected and _git(repo, "merge-base", "--is-ancestor", rejected, head).returncode == 0:
        start = rejected
    else:
        start = base
    r = _git(repo, "diff", start + ".." + head)
    if r.returncode:
        raise RuntimeError("git diff failed: " + r.stderr.strip())
    return r.stdout
