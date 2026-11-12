import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import limits as L


class Arbiter(unittest.TestCase):
    def test_first_reject_fixes(self):
        self.assertEqual(L.after_reject(["a"])[0], "FIX")

    def test_reject_reject_arbiter(self):
        self.assertEqual(L.after_reject(["a", "a"])[0], "ARBITER")

    def test_other_owner_is_not_second_reject_by_same(self):
        self.assertEqual(L.after_reject(["a", "b"])[0], "FIX")

    def test_only_the_last_two_count(self):
        self.assertEqual(L.after_reject(["a", "a", "b"])[0], "FIX")


if __name__ == "__main__":
    unittest.main()
