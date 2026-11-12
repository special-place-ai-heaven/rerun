import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E, runner_loop as R
from test_ready_start import Eng, T0


class Bad(Eng):
    def cancel(self, agent, rid):
        raise E.EngineError("down")


class LeaseSweep(unittest.TestCase):
    def go(self, eng):
        self.d = tempfile.TemporaryDirectory()
        cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(self.d.name, "t.json"),
               "store_file": os.path.join(self.d.name, "l.db"),
               "triggers": [{"stage": "build", "coworker": "CODE", "agent": "ag1", "slug": "factory-build"}]}
        self.eng, self.now = eng, T0
        eng.now = T0
        self.r = R.build(cfg, eng, clock=lambda: self.now)
        self.r.st.add_ready("j", "A", paths=["a.py"])
        self.r.tick()
        l = self.r.st.open_leases()
        self.now += 5000
        self.r.sweep_leases()
        return l[0]["id"] if l else None

    def tearDown(self):
        self.r.st.close()
        self.d.cleanup()

    def test_cancel_error_keeps_lease_open(self):
        self.go(Bad())
        self.assertEqual(len(self.r.st.open_leases()), 1)

    def test_cancel_ok_closes_lease(self):
        self.go(Eng())
        self.assertEqual(self.r.st.open_leases(), [])
        self.assertEqual(self.eng.cancelled, ["run1"])


if __name__ == "__main__":
    unittest.main()
