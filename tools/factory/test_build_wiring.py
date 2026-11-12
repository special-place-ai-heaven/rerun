import os, sys, tempfile, unittest
from types import SimpleNamespace as NS
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_ready_start import Eng, T0


class BuildWiring(unittest.TestCase):
    def test_build_end_runs_checkout_apply_testrun_publish(self):
        calls = []
        class CK:
            def __init__(s, path, url, base): calls.append("checkout")
            def ensure(s): return "p"
        saved = (R.CO, R.AP, R.TR, R.PB, R.EV)
        R.EV = NS(stage_check=lambda *a: ("OK", ""))
        R.CO = NS(Checkout=CK)
        R.AP = NS(apply=lambda w, p, a: calls.append("apply %s" % a) or "applied")
        R.TR = NS(run=lambda b, h, c: calls.append("testrun") or {"verdict": "ok"})
        R.PB = NS(publish=lambda w, j, t, b, o, paths: calls.append("publish %s" % paths))
        with tempfile.TemporaryDirectory() as d:
            cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(d, "t.json"),
                   "store_file": os.path.join(d, "l.db"),
                   "triggers": [{"stage": "build", "coworker": "CODE", "agent": "ag1", "slug": "factory-build"}]}
            eng = Eng(); eng.now = T0
            r = R.build(cfg, eng, clock=lambda: T0)
            try:
                r.st.add_ready("j", "A", paths=["a.py"])
                for k, v in dict(repo_url="u", base="b", base_branch="dev", title="t", **{"patch:A": "x", "test:A": "t a"}).items():
                    r.st.set("j", k, v)
                r.tick()
                eng.runs["run1"]["status"] = "done"
                r.tick()
            finally:
                R.CO, R.AP, R.TR, R.PB, R.EV = saved
                r.st.close()
        self.assertEqual(calls, ["checkout", "checkout", "apply ['a.py']", "testrun", "publish ['a.py']"])

    def test_build_passes_ghclient_open_pr(self):
        gh = NS(open_pr=lambda *a: None, get=lambda p: None, create_issue=lambda *a: None)
        with tempfile.TemporaryDirectory() as d:
            cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(d, "t.json"),
                   "store_file": os.path.join(d, "l.db"),
                   "triggers": [{"stage": "build", "coworker": "CODE", "agent": "ag1", "slug": "factory-build"}]}
            r = R.build(cfg, Eng(), clock=lambda: T0, gh=gh)
            r.st.close()
        self.assertIs(r.open_pr, gh.open_pr)


if __name__ == "__main__":
    unittest.main()
