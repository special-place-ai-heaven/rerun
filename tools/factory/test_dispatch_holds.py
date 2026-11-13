import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dispatch as D
import holds
from test_dispatch import World, ready, PR_LINE

SPENT = "AI_APICallError: You've hit your session limit · resets 3pm"


def issue(n):
    return {"number": n, "title": "Fix %d" % n, "body": ready(), "comments": []}


class Holds(unittest.TestCase):
    def make(self, issues):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.w = World(issues)
        cfg = {"repo": "o/r", "label": "factory", "max_jobs": 8, "checks_timeout_s": 3600, "auto_plan_marker": True,
               "ledger_file": os.path.join(tmp.name, "ledger.db"),
               "json_state_file": os.path.join(tmp.name, "dispatch.json"),
               "heartbeat_file": os.path.join(tmp.name, "heartbeat"),
               "builders": [{"id": b, "name": b.upper()} for b in ("b1", "b2")],
               "reviewers": [{"id": r, "name": r.upper()} for r in ("r1", "r2")]}
        self.w.ledger = cfg["ledger_file"]
        self.d = D.Dispatcher(cfg, self.w.account, self.w.gh, now=lambda: self.w.clock)
        self.addCleanup(self.d.close)

    def spend(self, agent):
        rid = [r for r, a in self.w.order if a == agent][-1]
        self.w.runs[rid] = {"status": "error", "error": SPENT, "output": None}

    def state(self, n):
        return self.d.store.get_job(str(n))["state"]

    def hold_until(self):
        h = holds.active(self.d.store, self.w.clock)
        return h and (h["kind"], h["until"])

    def test_a_spent_plan_puts_the_job_back_and_holds_all_sends_for_thirty_minutes(self):
        self.make([issue(5), issue(6)])
        self.d.once()
        self.assertEqual((self.state(5), self.state(6)), ("building", "building"))
        before = dict(self.d.store.get_job("5"))
        retries = self.w.rows("SELECT k, v FROM kv WHERE k LIKE 'retry:%'")
        t0 = self.w.clock
        self.spend("b1")
        self.w.finish("b2", PR_LINE)
        self.d.once()
        j = self.d.store.get_job("5")
        self.assertEqual(j["state"], "queued")
        self.assertEqual(j.get("attempt", 1), before.get("attempt", 1))
        self.assertEqual(self.w.rows("SELECT k, v FROM kv WHERE k LIKE 'retry:%'"), retries)
        self.assertEqual(len(self.w.sends), 2)
        self.assertEqual(self.hold_until(), ("plan limit", t0 + 1800))
        self.assertTrue(any(str(t["reason"]).startswith("plan limit: AI_APICallError") for t in self.d.store.transitions_of("5")))
        self.assertEqual(self.state(6), "review_wait")
        self.w.issues.append(issue(7))
        for _ in range(29):
            self.w.clock += 60
            self.d.once()
            self.assertEqual(len(self.w.sends), 2)
        self.assertEqual(self.state(7), "queued")
        self.assertEqual(self.state(5), "queued")
        self.assertEqual(self.state(6), "review_wait")
        self.w.clock = t0 + 1800
        self.d.once()
        self.assertGreater(len(self.w.sends), 2)

    def test_a_probe_that_hits_the_spent_plan_again_holds_again(self):
        self.make([issue(5)])
        self.d.once()
        self.spend("b1")
        self.d.once()
        self.w.clock += 1800
        self.d.once()
        self.assertEqual(self.state(5), "building")
        self.assertEqual(len(self.w.sends), 2)
        self.spend("b1")
        self.w.clock += 5
        self.d.once()
        self.assertEqual(self.state(5), "queued")
        self.assertEqual(self.hold_until(), ("plan limit", self.w.clock + 1800))


if __name__ == "__main__":
    unittest.main()
