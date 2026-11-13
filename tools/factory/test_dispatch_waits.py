import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dispatch as D
import holds
from test_dispatch import World, ready


def issue(n, deps="none"):
    return {"number": n, "title": "Fix %d" % n, "body": ready(deps=deps), "comments": []}


class Waits(unittest.TestCase):
    def make(self, issues):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.w = World(issues)
        cfg = {"repo": "o/r", "label": "factory", "checks_timeout_s": 3600, "auto_plan_marker": True,
               "ledger_file": os.path.join(tmp.name, "ledger.db"),
               "json_state_file": os.path.join(tmp.name, "dispatch.json"),
               "heartbeat_file": os.path.join(tmp.name, "heartbeat"),
               "types": {"coder": {"max_jobs": 8, "coworkers": [{"id": "c1", "name": "C1", "runs": 1}]},
                         "reviewer": {"coworkers": [{"id": "r1", "name": "R1", "runs": 1}]}}}
        self.w.ledger = cfg["ledger_file"]
        self.d = D.Dispatcher(cfg, self.w.account, self.w.gh, now=lambda: self.w.clock)
        self.addCleanup(self.d.close)

    def reason(self, n):
        return self.d.store.get_job(str(n)).get("wait_reason")

    def rows(self, n):
        return [t for t in self.d.store.transitions_of(str(n)) if str(t["reason"] or "").startswith("waits:")]

    def test_each_waiting_job_carries_one_reason_from_the_list_written_once(self):
        self.make([issue(1), issue(2), issue(3, deps="#7")])
        self.d.once()
        st = self.d.store
        self.assertEqual(st.get_job("1")["state"], "building")
        self.assertIsNone(self.reason(1))
        self.assertEqual(st.get_job("2")["state"], "queued")
        self.assertEqual(self.reason(2), "no free worker of its type")
        self.assertEqual(st.get_job("3")["state"], "waiting")
        self.assertEqual(self.reason(3), "dependency")
        self.assertEqual(len(self.rows(2)), 1)
        self.assertEqual(len(self.rows(3)), 1)
        self.assertEqual(self.rows(2)[0]["reason"], "waits: no free worker of its type")
        self.d.once()
        self.assertEqual(len(self.rows(2)), 1)
        self.assertEqual(len(self.rows(3)), 1)
        holds.arm(st, "plan limit", self.w.clock + 1800)
        self.d.once()
        self.assertEqual(self.reason(2), "plan limit")
        self.assertEqual(len(self.rows(2)), 2)
        j = st.get_job("2")
        j["not_before"] = self.w.clock + 60
        st.put_job("2", "queued", j)
        self.d.once()
        self.assertEqual(self.reason(2), "back-off")


if __name__ == "__main__":
    unittest.main()
