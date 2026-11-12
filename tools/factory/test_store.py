"""store.py tests: intent before fire, crash between intent and fire, refire count, resume, R6, single writer."""
import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store as S


class TestStore(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.p = os.path.join(self.d.name, "ledger.db")
        self.s = S.Store(self.p)

    def tearDown(self):
        self.s.close()
        self.d.cleanup()

    def test_wal(self):
        self.assertEqual(self.s.db.execute("PRAGMA journal_mode").fetchone()[0], "wal")

    def test_crash_between_intent_and_fire(self):
        fid = self.s.intent("60", "5", "build", "larry", "factory-build")
        self.s.close()  # crash: the fire happened or not, the run id was never stored
        self.s = S.Store(self.p)
        pend = self.s.pending("60")
        self.assertEqual([p["id"] for p in pend], [fid])
        self.assertIsNone(pend[0]["run_id"])
        self.assertEqual(self.s.resume("60")["last"]["status"], "intent")
        self.s.abandon(fid)
        self.assertEqual(self.s.pending("60"), [])

    def test_fire_and_close(self):
        fid = self.s.intent("60", "5", "build")
        self.s.fired(fid, "r1")
        self.assertEqual(self.s.running("60")[0]["run_id"], "r1")
        self.s.close_run("r1", "done", tokens_in=10, tokens_out=2)
        r = self.s.resume("60")
        self.assertEqual((r["running"], r["pending"]), ([], []))
        self.assertEqual((r["last"]["status"], r["last"]["tokens_in"]), ("done", 10))

    def test_refire_count(self):
        self.assertEqual(self.s.refires("60", "5", "build"), 0)
        self.s.fired(self.s.intent("60", "5", "build"), "r1")
        self.assertEqual(self.s.refires("60", "5", "build"), 0)
        self.s.close_run("r1", "error", error="engine restarted")
        f2 = self.s.intent("60", "5", "build")
        self.assertEqual(self.s.refires("60", "5", "build"), 1)
        self.assertEqual(self.s.pending("60")[0]["refire"], 1)
        self.assertEqual(self.s.refires("60", "6", "build"), 0)
        self.assertNotEqual(f2, 0)

    def test_resume_kv(self):
        self.s.set("60", "stage", "BUILD")
        self.s.set("60", "stage", "TEST")
        self.s.close()
        self.s = S.Store(self.p)
        self.assertEqual(self.s.resume("60")["state"], {"stage": "TEST"})
        self.assertIsNone(self.s.resume("61")["last"])

    def test_r6_foreign_runs(self):
        self.s.fired(self.s.intent("60", "5", "build"), "r1")
        self.assertEqual(self.s.foreign(["r1"]), [])
        self.assertEqual(self.s.foreign(["r1", "x9", "x8"]), ["x9", "x8"])
        self.assertEqual(self.s.foreign([]), [])

    def test_single_writer(self):
        with self.assertRaises(RuntimeError):
            S.Store(self.p)
        code = "import sys;sys.path.insert(0,%r);import store;store.Store(%r)" % (os.path.dirname(os.path.abspath(__file__)), self.p)
        r = subprocess.run([sys.executable, "-c", code], capture_output=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
