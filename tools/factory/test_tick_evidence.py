import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_runner_loop import FakeEngine, T0


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


if __name__ == "__main__":
    unittest.main()
