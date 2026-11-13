import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dispatch as D
from test_dispatch import World, PR_LINE, ready

LINE = "carries the issue number in its name"


def issue(n):
    return {"number": n, "title": "Fix %d" % n, "body": ready(), "comments": []}


class Copies(unittest.TestCase):
    def make(self, runs, issues):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.w = World(issues)
        self.cfg = {"repo": "o/r", "label": "factory", "checks_timeout_s": 3600, "auto_plan_marker": True,
                    "ledger_file": os.path.join(tmp.name, "ledger.db"),
                    "json_state_file": os.path.join(tmp.name, "dispatch.json"),
                    "heartbeat_file": os.path.join(tmp.name, "heartbeat"),
                    "types": {"coder": {"max_jobs": 8, "coworkers": [{"id": "c1", "name": "C1", "runs": runs}]},
                              "reviewer": {"coworkers": [{"id": "r1", "name": "R1", "runs": 1}]}}}
        self.w.ledger = self.cfg["ledger_file"]
        self.d = D.Dispatcher(self.cfg, self.w.account, self.w.gh, now=lambda: self.w.clock)
        self.addCleanup(self.d.close)

    def beat(self, n=1):
        for _ in range(n):
            self.d.once()

    def copies(self):
        return {int(j): c for j, c in ((j, self.d.store.get_job(j).get("copy")) for j in ("1", "2", "3", "4")
                                        if self.d.store.get_job(j))}

    def test_three_runs_of_one_coder_build_three_jobs_at_once_with_their_copy_on_the_ledger(self):
        self.make(3, [issue(n) for n in (1, 2, 3, 4)])
        self.beat()
        self.assertEqual([s[0] for s in self.w.sends], ["c1", "c1", "c1"])
        self.assertEqual(self.copies(), {1: 1, 2: 2, 3: 3, 4: None})
        self.assertEqual(self.d.store.get_job("4")["state"], "queued")
        self.w.runs["run2"] = {"status": "done", "output": PR_LINE, "error": None}
        self.beat()
        self.assertEqual(len(self.w.sends), 4)
        self.assertIn("rerun #4", self.w.sends[3][1])
        self.assertEqual(self.d.store.get_job("4")["copy"], 2)

    def test_with_one_run_each_a_coworker_takes_one_job_and_the_briefs_carry_the_file_name_line(self):
        self.make(1, [issue(1), issue(2)])
        self.beat(2)
        self.assertEqual(len(self.w.sends), 1)
        self.assertEqual(self.d.store.get_job("2")["state"], "queued")
        j = {"issue": 1, "title": "t", "round": 1}
        self.assertIn(LINE, D.build_brief(j))
        self.assertIn(LINE, D.fix_brief(j, 3, "no"))


if __name__ == "__main__":
    unittest.main()
