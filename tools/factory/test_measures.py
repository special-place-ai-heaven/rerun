import unittest
import measures


def t(s):
    return "2026-01-01T00:%02d:%02dZ" % divmod(s, 60)


class Queue(unittest.TestCase):
    def test_queue_measures(self):
        cfg = {"builder_capacity": 1}
        ready = [{"job": "j", "chunk": c, "added_at": t(0)} for c in "ABC"]
        fires = [{"job": "j", "chunk": "A", "stage": "build", "intent_at": t(10), "ended_at": t(30)},
                 {"job": "j", "chunk": "B", "stage": "build", "intent_at": t(40), "ended_at": None}]
        m = measures.queue_measures(ready, fires, t(60), cfg)
        self.assertEqual(m["depth"], 1)
        self.assertEqual(m["wait_s"], [10, 40, 60])
        # waiting from 0, slot free 0-10 and 30-40: 20 s; busy 10-30 and 40-60 do not count
        self.assertEqual(m["stalled_s"], 20)


class Occupancy(unittest.TestCase):
    def test_occupancy_quiet_nocommit_early_review(self):
        cfg = {"builder_capacity": 2}
        F = lambda c, st, a, b, who="x": {"job": "j", "chunk": c, "stage": st, "coworker": who, "intent_at": t(a), "ended_at": t(b) if b else None}
        fires = [F("A", "build", 0, 20), F("B", "build", 10, 30), F("A", "review", 25, 28, "rev")]
        wakes = [{"coworker": "rev", "at": t(24)}, {"coworker": "rev", "at": t(40)}]
        m = measures.occupancy_measures(fires, wakes, [("j", "A")], {"j": t(26)}, t(40), cfg)
        self.assertEqual((m["occupancy"], m["quiet_wake_rate"], m["no_commit"], m["early_reviews"]), (40 / 80, 0.5, 1, 1))
        self.assertIsNone(measures.occupancy_measures([], [], [], {}, t(40), cfg)["occupancy"])


if __name__ == "__main__":
    unittest.main()
