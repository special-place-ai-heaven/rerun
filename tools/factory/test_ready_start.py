import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_runner_loop import FakeEngine, T0


class Eng(FakeEngine):
    def list_triggers(self, agent):
        return [{"slug": "factory-build", "token": "tok"}]


class ReadyStart(unittest.TestCase):
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

    def test_three_slots_fourth_refused(self):
        for c in "ABCD":
            self.r.st.add_ready("j%s" % c, c, paths=[c + ".py"])
        self.r.tick()
        self.assertEqual(len(self.eng.fires), 3)
        self.assertEqual([x["chunk"] for x in self.r.st.ready_list()], ["D"])

    def test_requeue_bumps_attempt(self):
        self.r.st.add_ready("j", "A")
        self.r.tick()
        f = self.r.st.running()[0]
        self.r.requeue(f)
        self.assertEqual(self.r.st.attempts("j", "A"), 1)

    def test_requeue_one_path_and_closes_lease(self):
        self.r.st.add_ready("j", "A")
        self.r.tick()
        f = self.r.st.running()[0]
        self.r.st.grant_lease("j", "A", ["A.py"], "2099-01-01T00:00:00Z", attempt=f["refire"])
        self.r.requeue(f)
        self.assertEqual(self.r.st.db.execute("SELECT COUNT(*) FROM queue").fetchone()[0], 0)
        self.assertEqual(self.r.st.open_leases(), [])


if __name__ == "__main__":
    unittest.main()
