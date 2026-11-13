import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_runner_loop import FakeEngine, T0


class Eng(FakeEngine):
    def list_triggers(self, agent):
        return [{"slug": "factory-build", "token": "tok"}]


class ChainFailure(unittest.TestCase):
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

    def end_run(self):
        self.r.tick()
        f = self.r.st.running()[0]
        self.eng.runs[f["run_id"]]["status"] = "done"
        self.r.check(f)
        return f

    def test_first_failure_requeues_second_escalates(self):
        def boom(f):
            raise R.ChainFailed("done-test fail")
        self.r.finish_build = boom
        self.r.st.add_ready("j", "A", paths=["A.py"])
        self.end_run()
        self.assertEqual([x["chunk"] for x in self.r.st.ready_list()], ["A"])
        self.assertEqual(self.r.st.attempts("j", "A"), 1)
        self.end_run()
        self.assertEqual(self.r.st.ready_list(), [])
        self.assertEqual(self.r.st.db.execute("SELECT state FROM ready_chunks").fetchone()[0], "needs_boss")
        self.assertNotIn("done", [x[0] for x in self.r.st.db.execute("SELECT status FROM fires")])


if __name__ == "__main__":
    unittest.main()
