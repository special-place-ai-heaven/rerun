import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_arbiter_wire import Wire
from test_runner_loop import T0


class Issues:
    def __init__(self):
        self.made = []

    def create_issue(self, title, body=""):
        self.made.append(title)


class FollowupWire(Wire):
    def test_stage_done_creates_issue_once(self):
        c = Issues()
        self.r.issues = c
        v = "Verdict: pass\n- Follow-up: add a retry test\n"
        self.r.follow_up("71", v)
        self.r.follow_up("71", v)
        self.assertEqual(c.made, ["add a retry test"])
        self.assertEqual(len([k for k in self.r.st.get_all("71") if k.startswith("followup:")]), 1)


if __name__ == "__main__":
    unittest.main()
