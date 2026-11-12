import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_ready_start import Eng, T0


class LeaseResult(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(self.d.name, "t.json"),
               "store_file": os.path.join(self.d.name, "l.db"),
               "triggers": [{"stage": "build", "coworker": "CODE", "agent": "ag1", "slug": "factory-build"}]}
        self.eng = Eng()
        self.eng.now = T0
        self.r = R.build(cfg, self.eng, clock=lambda: T0)
        self.r.st.add_ready("j", "A", paths=["a.py"])
        self.r.tick()

    def tearDown(self):
        self.r.st.close()
        self.d.cleanup()

    def status(self):
        return self.r.st.db.execute("SELECT status FROM fires").fetchone()[0]

    def test_late_result_discarded(self):
        self.r.st.close_lease(self.r.st.open_leases()[0]["id"], "expired")
        self.eng.runs["run1"]["status"] = "done"
        self.r.tick()
        self.assertEqual(self.status(), "discarded")

    def test_result_under_open_lease_kept(self):
        self.eng.runs["run1"]["status"] = "done"
        self.r.tick()
        self.assertEqual(self.status(), "done")


if __name__ == "__main__":
    unittest.main()
