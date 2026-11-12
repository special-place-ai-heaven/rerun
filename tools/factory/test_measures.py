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


if __name__ == "__main__":
    unittest.main()
