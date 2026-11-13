import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakegh, ghclient


class FakeGhCompare(unittest.TestCase):
    def test_compare_returns_set_diff(self):
        f = fakegh.Fake()
        f.diffs[("job/71", "chunk/71-a")] = "diff --git a/x b/x\n+1\n"
        f.start()
        try:
            os.environ["GH_TOKEN_TEST"] = "t"
            c = ghclient.Client(f.url, "o/r", token_env="GH_TOKEN_TEST")
            self.assertEqual(c.compare_diff("job/71", "chunk/71-a"), "diff --git a/x b/x\n+1\n")
            with self.assertRaises(ghclient.GhError):
                c.compare_diff("job/71", "chunk/none")
        finally:
            f.stop()


if __name__ == "__main__":
    unittest.main()
