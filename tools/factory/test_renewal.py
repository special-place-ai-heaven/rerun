import unittest

import renewal


def conn(minutes, flag=True):
    return {"signIn": {"minutesLeft": minutes, "renewalDue": flag}}


class Renewal(unittest.TestCase):
    def test_the_smallest_time_left_decides_and_a_bad_answer_never_holds(self):
        both = {"default": "a", "connections": [conn(200), conn(40)]}
        self.assertEqual(renewal.left(both), 40)
        self.assertTrue(renewal.due(both, 50))
        self.assertFalse(renewal.due(both, 30))
        one = {"connections": [conn(200)]}
        self.assertFalse(renewal.due(one, 50))
        self.assertTrue(renewal.due({"connections": [conn(50)]}, 50))
        skipped = {"connections": [{"signIn": None}, conn(70)]}
        self.assertEqual(renewal.left(skipped), 70)
        for bad in (None, [], {}, {"connections": "x"}):
            self.assertIsNone(renewal.left(bad))
            self.assertFalse(renewal.due(bad, 50))


if __name__ == "__main__":
    unittest.main()
