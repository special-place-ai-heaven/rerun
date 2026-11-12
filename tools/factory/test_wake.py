import os
import tempfile
import unittest

import wake as W
from store import Store


class WakeBase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.st = Store(os.path.join(self.dir.name, "s.db"))
        self.ev = W.review_event(98)


class Claim(WakeBase):
    def test_event_name(self):
        self.assertEqual(self.ev, "review-ready:98")

    def test_repeat_event_starts_nothing(self):
        self.assertTrue(W.claim_wake(self.st, self.ev, "linus", "abc"))
        self.assertFalse(W.claim_wake(self.st, self.ev, "linus", "abc"))

    def test_new_head_or_coworker_starts(self):
        self.assertTrue(W.claim_wake(self.st, self.ev, "linus", "abc"))
        self.assertTrue(W.claim_wake(self.st, self.ev, "linus", "def"))
        self.assertTrue(W.claim_wake(self.st, self.ev, "ada", "abc"))


if __name__ == "__main__":
    unittest.main()
