import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R
from test_runner_loop import FakeEngine, T0


class Eng(FakeEngine):
    def list_triggers(self, agent):
        return [{"slug": "factory-build", "token": "tok"}]


class Base(unittest.TestCase):
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


def cs(*conc):
    return [{"name": "c%d" % i, "status": "completed" if c else "in_progress", "conclusion": c} for i, c in enumerate(conc)]


class ReviewFire(Base):
    def test_pending_or_red_fires_nothing(self):
        self.assertEqual(self.r.fire_reviews("j", 7, "abc", cs("success", None), ["A"]), [])
        self.assertEqual(self.r.fire_reviews("j", 7, "abc", cs("success", "failure"), ["A"]), [])
        self.assertEqual(self.queued(), [])

    def test_green_one_fire_per_owner(self):
        self.assertEqual(self.r.fire_reviews("j", 7, "abc", cs("success"), ["B", "A", "A"]), ["A", "B"])
        self.assertEqual(self.r.fire_reviews("j", 7, "abc", cs("success"), ["A", "B"]), [])
        self.assertEqual(len(self.queued()), 2)
        self.assertEqual({x[0] for x in self.r.st.db.execute("SELECT event FROM wakes")}, {"review-ready:7"})


if __name__ == "__main__":
    unittest.main()
