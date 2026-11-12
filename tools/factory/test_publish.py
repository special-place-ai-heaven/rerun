import os, subprocess, tempfile, unittest

import publish


def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Publish(unittest.TestCase):
    def test_push_bare_remote_and_pr_call(self):
        d = tempfile.mkdtemp()
        bare, wt = os.path.join(d, "r.git"), os.path.join(d, "wt")
        git(d, "init", "-q", "--bare", "-b", "dev", bare)
        git(d, "init", "-q", "-b", "dev", wt)
        git(wt, "remote", "add", "origin", bare)
        for k, v in (("user.name", "t"), ("user.email", "t@x")):
            git(wt, "config", k, v)
        open(os.path.join(wt, "a.txt"), "w").write("1")
        git(wt, "add", "."); git(wt, "commit", "-qm", "base")
        open(os.path.join(wt, "a.txt"), "w").write("2")
        calls = []
        sha = publish.publish(wt, 71, "C6e: x", "dev", lambda *a: calls.append(a) or "url")
        self.assertEqual(git(bare, "rev-parse", "factory/job-71"), sha)
        self.assertEqual(calls, [("C6e: x", "factory/job-71", "dev")])
