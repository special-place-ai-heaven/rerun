import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import applypatch

PATCH = "diff --git a/%s b/%s\n--- a/%s\n+++ b/%s\n@@ -1 +1 @@\n-one\n+two\n"


def patch(p):
    return PATCH % (p, p, p, p)


class ApplyPatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.w = self.tmp.name
        subprocess.run(["git", "init", "-q"], cwd=self.w, check=True)
        for f in ("ok.txt", "other.txt"):
            open(os.path.join(self.w, f), "w").write("one\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_applies_listed_path(self):
        self.assertEqual(applypatch.apply(self.w, patch("ok.txt"), ["ok.txt"]), "applied")
        self.assertEqual(open(os.path.join(self.w, "ok.txt")).read(), "two\n")

    def test_outside_path_is_oversized(self):
        self.assertEqual(applypatch.apply(self.w, patch("other.txt"), ["ok.txt"]), "oversized")
        self.assertEqual(open(os.path.join(self.w, "other.txt")).read(), "one\n")

    def test_over_80_lines_is_oversized(self):
        big = "diff --git a/ok.txt b/ok.txt\n--- a/ok.txt\n+++ b/ok.txt\n@@ -1 +1,90 @@\n-one\n" + "+x\n" * 90
        self.assertEqual(applypatch.apply(self.w, big, ["ok.txt"]), "oversized")


if __name__ == "__main__":
    unittest.main()
