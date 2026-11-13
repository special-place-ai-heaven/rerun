"""clocks.py (rerun#207): run clocks and retry class."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import clocks as C
import limits as L

CFG = {"run_limit_s": 2700, "stall_s": 600, "token_cap": 400000}


def run(steps=7, status="running", error=None, tokens=120000):
    return {"runId": "r1", "status": status, "steps": steps, "startedAt": "2026-11-13T18:00:00.000Z", "finishedAt": None,
            "error": error, "totalTokens": tokens,
            "goal": {"lastLineForms": [{"prefix": "PR:", "rest": "pull-url"}, {"prefix": "BLOCKED:", "rest": "sentence"}],
                     "turnLimit": 3, "state": "running", "verdicts": []}}


class Clocks(unittest.TestCase):
    def test_seen_after(self):
        first = C.seen_after(run(7), None, "2026-11-13T18:05:00Z")
        self.assertEqual(first, {"steps": 7, "at": "2026-11-13T18:00:00.000Z"})
        same = C.seen_after(run(7), first, "2026-11-13T18:06:00Z")
        self.assertEqual(same, first)
        self.assertEqual(C.seen_after(run(8), first, "2026-11-13T18:06:00Z"), {"steps": 8, "at": "2026-11-13T18:06:00Z"})

    def test_no_new_step_for_ten_minutes_cancels(self):
        now_iso = "2026-11-13T18:10:01Z"
        now = L.ts(now_iso)
        seen = {"steps": 7, "at": "2026-11-13T18:00:00Z"}
        kind, _ = C.outcome(run(7), C.seen_after(run(7), seen, now_iso), now, CFG)
        self.assertEqual(kind, "CANCEL")
        self.assertEqual(C.klass(kind), "cancel")
        kind, _ = C.outcome(run(8), C.seen_after(run(8), seen, now_iso), now, CFG)
        self.assertEqual(kind, "RUNNING")
        self.assertIsNone(C.klass(kind))

    def test_missing_and_restart(self):
        self.assertEqual(C.outcome(None, None, 0, CFG)[0], "MISSING")
        self.assertEqual(C.klass("MISSING"), "transient")
        r = run(status="error", error="interrupted: engine restarted")
        kind, _ = C.outcome(r, {"steps": 7, "at": r["startedAt"]}, L.ts("2026-11-13T18:01:00Z"), CFG)
        self.assertEqual((kind, C.klass(kind, r)), ("RESTARTED", "transient"))

    def test_rate_limit_and_no_room_are_transient(self):
        r = run(status="error", error="provider_overloaded: 429")
        kind, _ = C.outcome(r, {"steps": 7, "at": r["startedAt"]}, L.ts("2026-11-13T18:01:00Z"), CFG)
        self.assertEqual(kind, "REFIRE_ONCE")
        self.assertEqual(C.klass(kind, r), "transient")
        self.assertEqual(C.klass("FAILED", run(status="error", error="Rate Limit hit")), "transient")
        self.assertEqual(C.klass("FAILED", run(status="cancelled")), "work")
        self.assertEqual(C.klass("REFIRE_ONCE", run(status="error", error="boom")), "work")
        self.assertEqual(C.klass("BLOCKED", blocked="BLOCKED: 5 builders are already active (limit 2)"), "transient")
        self.assertEqual(C.klass("BLOCKED", blocked="BLOCKED: 3.1 GB free, floor is 5"), "transient")
        self.assertEqual(C.klass("BLOCKED", blocked="BLOCKED: 1 GB of memory available, floor is 2"), "transient")
        self.assertEqual(C.klass("BLOCKED", blocked="BLOCKED: /data/work is over 20 GB"), "transient")
        self.assertEqual(C.klass("BLOCKED", blocked="BLOCKED: plan: chunk needs a file outside its paths"), "plan")
        self.assertEqual(C.klass("BLOCKED", blocked="BLOCKED: Plan: x"), "plan")
        self.assertEqual(C.klass("BLOCKED", blocked="BLOCKED: tests fail"), "work")

    def test_backoff_is_one_two_four_minutes_then_none(self):
        self.assertEqual(C.RETRY_BACKOFF_S, (60, 120, 240))
        self.assertEqual([C.backoff(n) for n in (1, 2, 3, 4, 5)], [60, 120, 240, None, None])


if __name__ == "__main__":
    unittest.main()
