"""status_report.py tests with a fake ledger and a fake engine: every row, and the key never in the output."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import status_report as S

KEY = "sk-dev-SECRET-KEY-0123456789"


class FakeEngine:
    def __init__(self, runs):
        self.runs, self._key = runs, KEY  # the key is held, as in engine.Engine

    def get_run(self, agent, rid):
        return self.runs.get(rid)

    def list_runs(self, agent, status=None, limit=50):
        return [dict(r, id=i) for i, r in self.runs.items()]


def fire(run_id, status, intent="2026-11-12T10:00:00Z", ended="2026-11-12T10:01:10Z", stage="challenge", refire=0, job="j1"):
    return {"job": job, "chunk": "", "stage": stage, "coworker": "a1", "run_id": run_id, "status": status,
            "intent_at": intent, "ended_at": ended, "refire": refire}


def by(rows):
    return {r[0]: r for r in rows}


class TestReport(unittest.TestCase):
    def test_all_pass(self):
        fires = [fire("r-err", "error", ended="2026-11-12T10:00:30Z"), fire("r-ok", "done", refire=1),
                 fire("r-can", "cancelled", job="j2", stage="hold", ended="2026-11-12T10:30:00Z")]
        eng = FakeEngine({"r-err": {"status": "error"}, "r-ok": {"status": "done", "finishedAt": "2026-11-12T10:01:00Z"},
                          "r-can": {"status": "cancelled", "finishedAt": "2026-11-12T10:30:00Z"}})
        restart = S.ts("2026-11-12T10:00:45Z")
        r = by(S.report(fires, eng, ["a1"], restart))
        for k in ("R1", "R2", "R3", "R4", "R6"):
            self.assertEqual(r[k][1], "PASS", r[k])
        self.assertIn("seconds run-row-end-to-ledger=10", r["R1"][2])
        self.assertIn("refire count=1", r["R3"][2])
        self.assertIn("for a stage with no tools", r["R6"][2])

    def test_failures(self):
        fires = [fire("r1", "done", ended="2026-11-12T10:05:00Z"), fire("r2", "done"), fire("r3", "done")]
        eng = FakeEngine({"r1": {"status": "done", "finishedAt": "2026-11-12T10:01:00Z"}, "r2": {"status": "done"},
                          "r3": {"status": "done"}, "stray": {"status": "done"}})
        r = by(S.report(fires, eng, ["a1"], None))
        self.assertEqual([r[k][1] for k in ("R1", "R2", "R3", "R4", "R6")], ["FAIL"] * 5)
        self.assertIn("stray", r["R6"][2])

    def test_two_refires_fail_r3(self):
        fires = [fire("a", "error"), fire("b", "error", refire=1), fire("c", "done", refire=2)]
        eng = FakeEngine({"a": {"status": "error"}, "b": {"status": "error"}, "c": {"status": "done"}})
        self.assertEqual(by(S.report(fires, eng, ["a1"]))["R3"][1], "FAIL")

    def test_key_never_in_output(self):
        fires = [fire("r-ok", "done")]
        eng = FakeEngine({"r-ok": {"status": "done", "finishedAt": "2026-11-12T10:01:00Z"}})
        out = S.render(S.report(fires, eng, ["a1"], S.ts("2026-11-12T10:00:30Z")))
        self.assertNotIn(KEY, out)
        self.assertNotIn("SECRET", out)
        self.assertIn("R5: checked separately by the owner", out)

    def test_read_fires_uses_the_store_ledger(self):
        import tempfile, store
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ledger.db")
            s = store.Store(p)
            fid = s.intent("j", "", "challenge", "a1")
            s.fired(fid, "r9")
            rows = S.read_fires(p)  # while the writer lock is held
            s.close()
        self.assertEqual((rows[0]["run_id"], rows[0]["status"]), ("r9", "running"))


if __name__ == "__main__":
    unittest.main()
