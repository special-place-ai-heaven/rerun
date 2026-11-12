import os, tempfile, unittest
import store


class Attempts(unittest.TestCase):
    def setUp(self):
        self.p = os.path.join(tempfile.mkdtemp(), "s.db")
        self.s = store.Store(self.p)

    def test_refires_and_bump_share_counter(self):
        self.assertEqual(self.s.refires("j", "A", "build"), 0)
        self.assertEqual(self.s.bump_attempt("j", "A"), 1)
        self.assertEqual(self.s.refires("j", "A", "build"), 1)
        self.s.intent("j", "A", "build")  # first fire: already counted by the bump, no double count
        self.s.intent("j", "A", "build")
        self.assertEqual(self.s.refires("j", "A", "build"), 1)
        self.assertEqual(self.s.attempts("j", "A"), 1)
        self.assertEqual(self.s.ready_list("j"), [])


if __name__ == "__main__":
    unittest.main()
