import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_runner_loop as TR


class PacketRefuse(unittest.TestCase):
    setUp, tearDown, make, make_with, tick = (getattr(TR.TestRunner, n) for n in ("setUp", "tearDown", "make", "make_with", "tick"))

    def test_oversized_refused_at_fire(self):
        st = self.runner.st
        st.enqueue("70", "challenge", "C1", {"job": "70", "text": "a" * 5000})
        st.enqueue("71", "challenge", "C1", {"job": "71", "text": "ok"})
        self.tick()
        self.assertEqual([f[1]["job"] for f in self.eng.fires], ["71"])
        self.assertEqual(st.fire_count("70"), 0)
        self.assertEqual([q["job"] for q in st.queued(TR.R.iso(self.now + 1))], [])


if __name__ == "__main__":
    unittest.main()
