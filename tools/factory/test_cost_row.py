import os, sqlite3, tempfile, unittest
import store


class CostRow(unittest.TestCase):
    def setUp(self):
        self.p = os.path.join(tempfile.mkdtemp(), "s.db")
        self.s = store.Store(self.p)

    def tearDown(self):
        self.s.close()

    def test_row_has_tokens_and_seconds(self):
        f = self.s.intent("j", "A", "build", at="2026-01-01T00:00:00Z")
        self.s.fired(f, "r1")
        self.s.close_run("r1", "done", at="2026-01-01T00:01:30Z", tokens_in=100, tokens_out=20,
                         cache_read=500, cache_write=40)
        c = self.s.stage_cost("r1")
        self.assertEqual((c["tokens_in"], c["tokens_out"], c["cache_read"], c["cache_write"], c["seconds"]),
                         (100, 20, 500, 40, 90))

    def test_absent_cache_is_none(self):
        f = self.s.intent("j", "A", "build", at="2026-01-01T00:00:00Z")
        self.s.fired(f, "r2")
        self.s.close_run("r2", "done", at="2026-01-01T00:00:05Z", tokens_in=1, tokens_out=2)
        c = self.s.stage_cost("r2")
        self.assertIsNone(c["cache_read"])
        self.assertEqual(c["seconds"], 5)

    def test_old_db_gets_columns(self):
        self.s.close()
        db = sqlite3.connect(self.p)
        db.execute("ALTER TABLE fires DROP COLUMN seconds")
        db.execute("ALTER TABLE fires DROP COLUMN cache_read")
        db.execute("ALTER TABLE fires DROP COLUMN cache_write")
        db.commit(); db.close()
        self.s = store.Store(self.p)
        f = self.s.intent("j", "A", "build", at="2026-01-01T00:00:00Z")
        self.s.fired(f, "r3")
        self.s.close_run("r3", "done", at="2026-01-01T00:00:02Z", cache_read=7)
        self.assertEqual(self.s.stage_cost("r3")["cache_read"], 7)


if __name__ == "__main__":
    unittest.main()
