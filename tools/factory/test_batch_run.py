import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_runner_loop import FakeEngine, T0


class Eng(FakeEngine):
    def list_triggers(self, agent):
        return [{"slug": "factory-build", "token": "tok"}]


class Batch(unittest.TestCase):
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


class BatchRun(Batch):
    def test_each_chunk_own_lease_shared_expiry(self):
        for c in "AB":
            self.r.st.add_ready("j", c, paths=[c + ".py"])
        self.assertEqual(self.r.fire_batch(self.r.st.ready_list()), "run1")
        ls = self.r.st.open_leases()
        self.assertEqual(sorted(l["chunk"] for l in ls), ["A", "B"])
        self.assertEqual(len({l["expires_at"] for l in ls}), 1)
        self.assertEqual(len(self.eng.fires), 1)
        rows = self.r.st.db.execute("SELECT chunk, run_id, status FROM fires ORDER BY chunk").fetchall()
        self.assertEqual([tuple(x) for x in rows], [("A", "run1", "running"), ("B", "run1", "running")])

    def test_trigger_error_is_caught(self):
        import trigger as T
        for c in "AB":
            self.r.st.add_ready("j", c, paths=[c + ".py"])
        def boom(*a, **k):
            raise T.TriggerError("down")
        old, R.T.fire = R.T.fire, boom
        try:
            self.assertIsNone(self.r.fire_batch(self.r.st.ready_list()))
        finally:
            R.T.fire = old
        self.assertEqual(self.r.st.db.execute("SELECT COUNT(*) FROM fires WHERE status='intent'").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main()
