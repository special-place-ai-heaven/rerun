import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_runner_loop as TR


class JobTotal(unittest.TestCase):
    setUp, tearDown, make, make_with, tick = (getattr(TR.TestRunner, n) for n in ("setUp", "tearDown", "make", "make_with", "tick"))

    def test_over_total_stops_firing(self):
        self.cfg["job_token_cap"] = 100
        self.runner.st.close()
        self.runner = self.make()
        st = self.runner.st
        st.enqueue("80", "challenge", "C1")
        self.tick()
        self.eng.runs["run1"].update(status="done", inputTokens=90, outputTokens=20)
        self.tick()
        st.enqueue("80", "challenge", "C2")
        st.enqueue("81", "challenge", "C1")
        self.tick()
        self.assertEqual([f[1]["job"] for f in self.eng.fires], ["80", "81"])
        self.assertEqual(st.fire_count("80"), 1)
        self.assertEqual(st.queued(TR.R.iso(self.now + 1)), [])


if __name__ == "__main__":
    unittest.main()
