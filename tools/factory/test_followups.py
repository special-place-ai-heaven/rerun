import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import followups as F

V = "Verdict: pass\n- Follow-up: add a retry test\nnon-blocking: rename helper\n* FOLLOW-UP: document the key\nplain line\n"


class Notes(unittest.TestCase):
    def test_three_notes_three_keys(self):
        n = F.notes(V, "71")
        self.assertEqual(len(n), 3)
        self.assertEqual(len({k for k, _, _ in n}), 3)
        self.assertEqual(F.notes(V, "71"), n)
        self.assertEqual(F.known([n[0][2], None]), {n[0][0]})


if __name__ == "__main__":
    unittest.main()
