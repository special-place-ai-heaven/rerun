import os, tempfile, unittest
import store


class WakeStore(unittest.TestCase):
    def setUp(self):
        self.p = os.path.join(tempfile.mkdtemp(), "s.db")
        self.s = store.Store(self.p)

    def test_unique_key_and_release(self):
        self.assertTrue(self.s.add_wake("ci", "linus", "abc"))
        self.assertFalse(self.s.add_wake("ci", "linus", "abc"))
        self.assertTrue(self.s.add_wake("ci", "linus", "def"))
        self.assertTrue(self.s.release_wake("ci", "linus", "abc"))
        self.assertFalse(self.s.release_wake("ci", "linus", "abc"))
        self.assertTrue(self.s.add_wake("ci", "linus", "abc"))


if __name__ == "__main__":
    unittest.main()
