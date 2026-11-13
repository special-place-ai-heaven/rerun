import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_runner_loop import FakeEngine, T0
from test_ready_start import Eng


class TickEvidence(unittest.TestCase):
    def test_done_only_with_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(d, "t.json"),
                   "store_file": os.path.join(d, "l.db"),
                   "triggers": [{"stage": "challenge", "coworker": "DA", "agent": "ag1", "slug": "factory-challenge"}]}
            eng = FakeEngine(); eng.now = T0
            r = R.build(cfg, eng, clock=lambda: T0)
            seen = [("NONE", "not pushed")]
            r.evidence = lambda f: seen[0]
            r.st.enqueue("j", "challenge")
            r.tick()
            eng.runs["run1"]["status"] = "done"
            r.tick()
            before = r.st.running()[0]["status"]
            seen[0] = ("OK", {})
            r.tick()
            after = r.st.db.execute("SELECT status FROM fires").fetchone()[0]
            r.st.close()
        self.assertEqual((before, after), ("running", "done"))

    def test_build_sets_evidence_callable(self):
        from types import SimpleNamespace as NS
        gh = NS(get=lambda p: None, open_pr=lambda *a: None, create_issue=lambda *a: None)
        seen, saved = [], R.EV
        R.EV = NS(stage_check=lambda get, f, kv, ready: seen.append((get, f["chunk"], kv["repo_url"], ready["paths"])) or ("OK", "x"))
        with tempfile.TemporaryDirectory() as d:
            cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(d, "t.json"),
                   "store_file": os.path.join(d, "l.db"),
                   "triggers": [{"stage": "build", "coworker": "CODE", "agent": "ag1", "slug": "factory-build"}]}
            try:
                r = R.build(cfg, Eng(), clock=lambda: T0, gh=gh)
                r.st.add_ready("j", "A", paths=["a.py"])
                r.st.set("j", "repo_url", "u")
                got = r.evidence({"stage": "build", "job": "j", "chunk": "A"})
                r.st.close()
            finally:
                R.EV = saved
        self.assertEqual((got, seen), (("OK", "x"), [(gh.get, "A", "u", ["a.py"])]))


if __name__ == "__main__":
    unittest.main()
