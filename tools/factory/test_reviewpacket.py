import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reviewpacket as R


class ReviewPacket(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)

    def git(self, *a):
        r = subprocess.run(["git", "-C", self.d.name, "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def commit(self, name, text):
        with open(os.path.join(self.d.name, name), "w") as f:
            f.write(text)
        self.git("add", name)
        self.git("commit", "-m", name)
        return self.git("rev-parse", "HEAD")

    def test_only_later_change(self):
        self.git("init", "-q")
        base = self.commit("base.txt", "base\n")
        rejected = self.commit("first.txt", "first\n")
        head = self.commit("second.txt", "second\n")
        diff = R.review_diff(self.d.name, base, head, rejected)
        self.assertIn("second.txt", diff)
        self.assertNotIn("first.txt", diff)

    def test_full_diff_when_not_ancestor(self):
        self.git("init", "-q")
        base = self.commit("base.txt", "base\n")
        rejected = self.commit("first.txt", "first\n")
        self.git("reset", "-q", "--hard", base)
        head = self.commit("other.txt", "other\n")
        diff = R.review_diff(self.d.name, base, head, rejected)
        self.assertIn("other.txt", diff)
        self.assertNotIn("first.txt", diff)
        self.assertIn("other.txt", R.review_diff(self.d.name, base, head))


if __name__ == "__main__":
    unittest.main()
