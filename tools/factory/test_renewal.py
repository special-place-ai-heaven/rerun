import unittest

import renewal


class Renewal(unittest.TestCase):
    def test_only_the_default_connection_decides_and_a_bad_answer_never_holds(self):
        def c(minutes, default, i="x"):
            sign_in = None if minutes is None else {
                "minutesLeft": minutes, "renewalDue": minutes < 60}
            return {"id": i, "provider": "claude", "isDefault": default,
                    "signIn": sign_in}

        a = {"connections": [c(200, True, "a"), c(0, False, "b")]}
        self.assertEqual(renewal.left(a), 200)
        self.assertFalse(renewal.due(a, 50))
        for minutes, expect in ((40, True), (50, True), (51, False)):
            a = {"connections": [c(minutes, True, "a"), c(200, False, "b")]}
            self.assertEqual(renewal.left(a), minutes)
            self.assertEqual(renewal.due(a, 50), expect)
        a = {"connections": [c(None, True, "a"), c(10, False, "b")]}
        self.assertIsNone(renewal.left(a))
        self.assertFalse(renewal.due(a, 50))
        a = {"connections": [c(10, False, "a"), c(5, False, "b")]}
        self.assertIsNone(renewal.left(a))
        self.assertFalse(renewal.due(a, 50))
        for bad in (None, [], {}, {"connections": "x"}):
            self.assertIsNone(renewal.left(bad))
            self.assertFalse(renewal.due(bad, 50))


if __name__ == "__main__":
    unittest.main()
