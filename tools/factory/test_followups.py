import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import followups as F

V = "Verdict: pass\n- Follow-up: add a retry test\nnon-blocking: rename helper\n* FOLLOW-UP: document the key\nplain line\n"


class Client:
    def __init__(self):
        self.made = []

    def create_issue(self, title, body=""):
        self.made.append((title, body))


class Notes(unittest.TestCase):
    def test_three_notes_three_keys(self):
        n = F.notes(V, "71")
        self.assertEqual(len(n), 3)
        self.assertEqual(len({k for k, _, _ in n}), 3)
        self.assertEqual(F.notes(V, "71"), n)
        self.assertEqual(F.known([n[0][2], None]), {n[0][0]})


class Create(unittest.TestCase):
    def test_rerun_creates_zero(self):
        c = Client()
        n = F.notes(V, "71")
        self.assertEqual(len(F.create(c, n)), 3)
        keys = F.known([b for _, b in c.made])
        self.assertEqual(F.create(c, n, keys), [])
        self.assertEqual(len(c.made), 3)


if __name__ == "__main__":
    unittest.main()
