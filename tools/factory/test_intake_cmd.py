import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
import store
from test_intake import OK1, OK2, plan


class FakeGh:
    def issue(self, n): return {"title": "rerun#%d" % n, "body": "goal"}
    def comments(self, n): return [{"body": plan(OK1, OK2)}]
    def branch_sha(self, b): return "sha-of-" + b


class IntakeCmd(unittest.TestCase):
    def test_issue_becomes_job_with_base_sha(self):
        with tempfile.TemporaryDirectory() as d:
            st = store.Store(os.path.join(d, "s.db"))
            state, errors = R.intake_issue(st, FakeGh(), "o/r", 71)
            kv = st.get_all("71")
            self.assertEqual((errors, sorted(state["chunks"])), ([], ["A1", "A2"]))
            self.assertEqual((kv["base"], kv["base_branch"], kv["title"], kv["repo_url"]),
                             ("sha-of-dev", "dev", "rerun#71", "https://github.com/o/r"))
            self.assertEqual(len(st.ready_list("71")), 2)
            st.close()

    def test_no_plan_stores_no_base(self):
        gh = FakeGh(); gh.comments = lambda n: []
        with tempfile.TemporaryDirectory() as d:
            st = store.Store(os.path.join(d, "s.db"))
            self.assertIsNone(R.intake_issue(st, gh, "o/r", 71)[0])
            self.assertEqual(st.get_all("71"), {})
            st.close()


if __name__ == "__main__":
    unittest.main()
