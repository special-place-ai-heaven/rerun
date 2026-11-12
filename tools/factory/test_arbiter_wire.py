import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_runner_loop import FakeEngine, T0


class Eng(FakeEngine):
    def list_triggers(self, agent):
        return [{"slug": "factory-build", "token": "tok"}]


class Wire(unittest.TestCase):
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

    def queued(self):
        return [x[0] for x in self.r.st.db.execute("SELECT stage FROM queue")]


class ArbiterWire(Wire):
    def test_second_reject_queues_arbiter(self):
        self.assertEqual(self.r.after_reject("j", "A", ["x", "x"]), "ARBITER")
        self.assertEqual(self.queued(), ["arbiter"])

    def test_first_reject_queues_nothing(self):
        self.assertEqual(self.r.after_reject("j", "A", ["x"]), "FIX")
        self.assertEqual(self.queued(), [])


if __name__ == "__main__":
    unittest.main()
