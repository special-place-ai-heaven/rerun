import os, sys, tempfile, unittest
from types import SimpleNamespace as NS
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_ready_start import Eng, T0


class RunGate(unittest.TestCase):
    def finish(self, run):
        saved = (R.CO, R.AP, R.TR, R.PB, R.EV)
        R.EV = NS(stage_check=lambda *a: ("OK", ""))
        R.CO = NS(Checkout=lambda p, u, b: NS(ensure=lambda: "p"))
        R.AP = NS(apply=lambda w, p, a: "applied")
        R.TR = NS(run=lambda b, h, c: {"verdict": "ok"})
        R.PB = NS(publish=lambda *a: None)
        gh = NS(open_pr=lambda *a: None, pr_by_head=lambda b: {"number": 7, "merged": False}, create_issue=lambda *a: None, get=lambda p: None)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(R.subprocess, "run", run):
            cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(d, "t.json"),
                   "store_file": os.path.join(d, "l.db"),
                   "triggers": [{"stage": "build", "coworker": "CODE", "agent": "ag1", "slug": "factory-build"}]}
            eng = Eng(); eng.now = T0
            r = R.build(cfg, eng, clock=lambda: T0, gh=gh)
            try:
                r.st.add_ready("j", "A", paths=["a.py"])
                for k, v in dict(repo_url="https://github.com/o/r", base="b", base_branch="dev", title="t", **{"patch:A": "x", "test:A": "t a"}).items():
                    r.st.set("j", k, v)
                r.tick()
                eng.runs["run1"]["status"] = "done"
                r.tick()
                return r.st.get_all("j")
            finally:
                R.CO, R.AP, R.TR, R.PB, R.EV = saved
                r.st.close()

    def test_gate_child_has_post_status_env(self):
        seen = {}
        def run(cmd, **kw):
            seen.update(cmd=cmd, env=kw["env"])
            return NS(returncode=0)
        kv = self.finish(run)
        self.assertEqual(seen["cmd"][-2:], ["o/r", "7"])
        self.assertTrue(seen["cmd"][-3].endswith("gate.py"))
        self.assertEqual((seen["env"]["GATE_POST_STATUS"], seen["env"]["FACTORY_GH"]), ("1", "gh"))
        self.assertTrue(seen["env"]["FACTORY_WORK"].startswith(os.environ.get("FACTORY_DATA_DIR", "/state") + "/"))
        self.assertEqual(kv["published:A"], "1")

    def test_gate_crash_keeps_chunk_published(self):
        def run(cmd, **kw): raise OSError("boom")
        self.assertEqual(self.finish(run)["published:A"], "1")


if __name__ == "__main__":
    unittest.main()
