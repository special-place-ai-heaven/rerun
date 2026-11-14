import contextlib, io, os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dispatch as D
import holds
from test_dispatch import World, ready, PR_LINE


def issue(n):
    return {"number": n, "title": "Fix %d" % n, "body": ready(), "comments": []}


class Account(World):
    """A World whose account also answers list_ai_connections."""
    sign_in = {"minutesLeft": 120, "renewalDue": True}
    broken = False

    def account(self, tool, args):
        if tool == "list_ai_connections":
            if self.broken:
                raise KeyError("list_ai_connections")
            return {"connections": [{"id": "c1", "provider": "claude", "isDefault": True,
                                 "signIn": self.sign_in}]}
        return super().account(tool, args)


class Renewal(unittest.TestCase):
    def make(self, issues):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.w = Account(issues)
        cfg = {"repo": "o/r", "label": "factory", "max_jobs": 8, "checks_timeout_s": 3600, "auto_plan_marker": True,
               "poll_s": 30, "clocks": {"run_limit_s": 2700},
               "ledger_file": os.path.join(tmp.name, "ledger.db"),
               "json_state_file": os.path.join(tmp.name, "dispatch.json"),
               "heartbeat_file": os.path.join(tmp.name, "heartbeat"),
               "builders": [{"id": b, "name": b.upper()} for b in ("b1", "b2")],
               "reviewers": [{"id": r, "name": r.upper()} for r in ("r1", "r2")]}
        self.w.ledger = cfg["ledger_file"]
        self.d = D.Dispatcher(cfg, self.w.account, self.w.gh, now=lambda: self.w.clock)
        self.addCleanup(self.d.close)
        self.out = io.StringIO()

    def beat(self):
        with contextlib.redirect_stdout(self.out):
            self.d.once()

    def state(self, n):
        return self.d.store.get_job(str(n))["state"]

    def hold(self):
        return holds.active(self.d.store, self.w.clock)

    def test_a_sign_in_about_to_run_out_holds_new_sends_and_lets_the_runs_out_end(self):
        self.make([issue(5)])
        self.beat()
        self.assertEqual((self.state(5), len(self.w.sends)), ("building", 1))
        self.assertIsNone(self.hold())
        self.w.issues.append(issue(6))
        self.w.sign_in = {"minutesLeft": 50, "renewalDue": True}
        self.w.clock += 30
        self.w.finish("b1", PR_LINE)
        self.beat()
        self.assertEqual(self.state(5), "review_wait")
        self.assertEqual(self.state(6), "queued")
        self.assertEqual(len(self.w.sends), 1)
        self.assertEqual(self.hold()["kind"], "sign-in renewal")
        self.assertEqual(self.out.getvalue().count("sign-in has 50 min left"), 1)
        self.w.sign_in = {"minutesLeft": 480, "renewalDue": False}
        self.w.clock += 30
        self.beat()
        self.assertIsNone(self.hold())
        self.assertEqual(len(self.w.sends), 3)
        self.assertEqual(self.state(6), "building")

    def test_a_failed_read_leaves_the_hold_as_it_is(self):
        self.make([])
        self.w.sign_in = {"minutesLeft": 50}
        self.beat()
        t0 = self.w.clock
        self.assertEqual(self.hold()["until"], t0 + 60)
        self.w.broken = True
        for _ in range(3):
            self.beat()
        self.assertEqual(self.hold()["until"], t0 + 60)
        self.assertEqual(self.out.getvalue().count("sign-in time not readable"), 1)
        self.assertNotIn("KeyError", self.out.getvalue())
        self.w.broken = False
        self.w.clock += 10
        self.beat()
        self.assertEqual(self.hold()["until"], t0 + 70)
        self.w.broken = True
        self.beat()
        self.assertEqual(self.out.getvalue().count("sign-in time not readable"), 2)


if __name__ == "__main__":
    unittest.main()
