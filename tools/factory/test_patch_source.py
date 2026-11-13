import os, sys, tempfile, unittest
from types import SimpleNamespace as NS
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_ready_start import Eng, T0


class PatchSource(unittest.TestCase):
    def run_build(self, kv, gh):
        seen = {}
        class CK:
            def __init__(s, path, url, base): pass
            def ensure(s): return "p"
        saved = (R.CO, R.AP, R.TR, R.PB, R.EV)
        R.EV = NS(stage_check=lambda *a: ("OK", ""))
        R.CO = NS(Checkout=CK)
        R.AP = NS(apply=lambda w, p, a: seen.update(patch=p) or "applied")
        R.TR = NS(run=lambda b, h, c: {"verdict": "ok"})
        R.PB = NS(publish=lambda *a: None)
        with tempfile.TemporaryDirectory() as d:
            cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(d, "t.json"),
                   "store_file": os.path.join(d, "l.db"),
                   "triggers": [{"stage": "build", "coworker": "CODE", "agent": "ag1", "slug": "factory-build"}]}
            eng = Eng(); eng.now = T0
            r = R.build(cfg, eng, clock=lambda: T0, gh=gh)
            try:
                r.st.add_ready("j", "A", paths=["a.py"])
                for k, v in dict(repo_url="u", base="b", base_branch="dev", title="t", **{"test:A": "t a"}, **kv).items():
                    r.st.set("j", k, v)
                r.tick()
                eng.runs["run1"]["status"] = "done"
                r.tick()
                seen["kv"] = r.st.get_all("j")
            finally:
                R.CO, R.AP, R.TR, R.PB, R.EV = saved
                r.st.close()
        return seen

    def test_patch_taken_from_pushed_branch(self):
        asked = []
        gh = NS(open_pr=lambda *a: None, pr_by_head=lambda b: None, create_issue=lambda *a: None, get=lambda p: None,
                compare_diff=lambda b, br: asked.append((b, br)) or "DIFF")
        seen = self.run_build({}, gh)
        self.assertEqual(asked, [("b", "chunk/j-A")])
        self.assertEqual(seen["patch"], "DIFF")
        self.assertEqual(seen["kv"]["patch:A"], "DIFF")

    def test_given_patch_is_kept(self):
        gh = NS(open_pr=lambda *a: None, pr_by_head=lambda b: None, create_issue=lambda *a: None, get=lambda p: None,
                compare_diff=lambda b, br: self.fail("must not fetch"))
        self.assertEqual(self.run_build({"patch:A": "GIVEN"}, gh)["patch"], "GIVEN")


if __name__ == "__main__":
    unittest.main()
