import os, sys, tempfile, unittest, unittest.mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import testrun

CMD = [sys.executable, "-c", "import sys; sys.exit(0 if open('v').read() == 'new' else 1)"]


class TestRun(unittest.TestCase):
    def tree(self, text):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        open(os.path.join(d.name, "v"), "w").write(text)
        return d.name

    def test_fail_before_pass_after(self):
        r = testrun.run(self.tree("old"), self.tree("new"), CMD)
        self.assertEqual((r["verdict"], r["base"], r["head"]), ("ok", 1, 0))

    def test_not_failing_on_base_or_failing_on_head(self):
        self.assertEqual(testrun.run(self.tree("new"), self.tree("new"), CMD)["verdict"], "passes_on_base")
        self.assertEqual(testrun.run(self.tree("old"), self.tree("old"), CMD)["verdict"], "fails_on_head")

    def test_child_cannot_see_credentials(self):
        cmd = [sys.executable, "-c", "import os, sys; sys.exit(1 if 'FACTORY_GIT_TOKEN' in os.environ or 'GIT_ASKPASS' in os.environ else 0)"]
        with unittest.mock.patch.dict(os.environ, {"FACTORY_GIT_TOKEN": "fake", "GIT_ASKPASS": "/fake"}):
            self.assertEqual(testrun._rc(self.tree("x"), cmd, 30), 0)


if __name__ == "__main__":
    unittest.main()
