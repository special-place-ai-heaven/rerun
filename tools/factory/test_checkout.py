import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checkout

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def git(cwd, *a):
    return subprocess.run(["git", *a], cwd=cwd, env=ENV, check=True, capture_output=True, text=True).stdout.strip()


class Checkout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "src")
        os.makedirs(self.src)
        git(self.src, "init", "-q")
        open(os.path.join(self.src, "a.txt"), "w").write("one")
        git(self.src, "add", ".")
        git(self.src, "commit", "-qm", "c1")
        self.base = git(self.src, "rev-parse", "HEAD")
        open(os.path.join(self.src, "a.txt"), "w").write("two")
        git(self.src, "commit", "-qam", "c2")
        self.co = checkout.Checkout(os.path.join(self.tmp.name, "co"), self.src, self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pinned_base(self):
        self.co.ensure()
        self.assertEqual(self.co.reader().open("a.txt").read(), "one")

    def test_reader_refuses_write(self):
        self.co.ensure()
        for rel, mode in (("a.txt", "w"), ("a.txt", "r+"), ("../x", "r")):
            with self.assertRaises(PermissionError):
                self.co.reader().open(rel, mode)


if __name__ == "__main__":
    unittest.main()
