import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_runner_loop import FakeEngine, T0


class Issues:
    def __init__(self):
        self.made = []

    def create_issue(self, title, body=""):
        self.made.append(title)


class Eng(FakeEngine):
    def list_triggers(self, agent):
        return [{"slug": "factory-review", "token": "tok"}]


class FollowupWire(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(self.d.name, "t.json"),
               "store_file": os.path.join(self.d.name, "l.db"),
               "triggers": [{"stage": "review", "coworker": "R", "agent": "ag1", "slug": "factory-review"}]}
        self.eng = Eng()
        self.eng.now = T0
        self.r = R.build(cfg, self.eng, clock=lambda: T0)
        self.r.issues = Issues()

    def tearDown(self):
        self.r.st.close()
        self.d.cleanup()

    def review_done(self, job, ev, run):
        self.r.evidence = lambda f: ev
        self.r.st.enqueue(job, "review")
        self.r.tick()
        self.eng.runs[run]["status"] = "done"
        self.r.tick()
        return self.r.st.db.execute("SELECT status FROM fires WHERE run_id=?", (run,)).fetchone()[0]

    def test_review_done_creates_issue_once(self):
        v = "Verdict: pass\n- Follow-up: add a retry test\n"
        self.assertEqual(self.review_done("71", ("OK", v), "run1"), "done")
        self.assertEqual(self.review_done("71", ("OK", v), "run2"), "done")
        self.assertEqual(self.r.issues.made, ["add a retry test"])

    def test_dict_evidence_closes_without_issue(self):
        self.assertEqual(self.review_done("71", ("OK", {"k": 1}), "run1"), "done")
        self.assertEqual(self.r.issues.made, [])


if __name__ == "__main__":
    unittest.main()
