import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_ready_start import Eng, T0


class StartBatch(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(self.d.name, "t.json"),
               "store_file": os.path.join(self.d.name, "l.db"),
               "triggers": [{"stage": "build", "coworker": "CODE", "agent": "ag1", "slug": "factory-build"}]}
        self.eng = Eng()
        self.eng.now = T0
        self.r = R.build(cfg, self.eng, clock=lambda: T0)

    def tearDown(self):
        self.r.st.close()
        self.d.cleanup()

    def test_start_ready_fires_one_run_per_batch(self):
        for j, c in (("j", "A"), ("j", "B"), ("k", "C")):
            self.r.st.add_ready(j, c, paths=[c + ".py"])
        self.r.start_ready()
        self.assertEqual([p["chunks"] for _, p in self.eng.fires], [["A", "B"], ["C"]])
        self.assertEqual(len(self.r.st.open_leases()), 3)
        self.assertEqual(self.r.st.ready_list(), [])


if __name__ == "__main__":
    unittest.main()
