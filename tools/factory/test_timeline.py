"""timeline.py tests: ledgers are made by store.Store on a temp folder, read through the read-only reader."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import store
import timeline as T

D = "2026-11-13T"


def at(hm):
    return D + hm + ":00Z"


class Timeline(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "ledger.db")
        self.st = store.Store(self.path)
        self.addCleanup(self._close)

    def _close(self):
        try:
            self.st.close()
        except Exception:
            pass

    def test_gantt_from_a_real_ledger(self):
        for state, hm in (("queued", "18:06"), ("building", "18:06"), ("review_wait", "18:08"), ("merged", "18:16")):
            self.st.put_job("171", state, {}, at=at(hm))
        rows = T.read_rows(self.path)
        out = T.gantt(rows, T.parse(at("18:30")), T.parse(at("00:00")))
        self.assertEqual(out, "\n".join([
            "```mermaid",
            "gantt",
            "    title Factory jobs, times in UTC",
            "    dateFormat HH:mm",
            "    axisFormat %H:%M",
            "    section 171",
            "    171 queued :done, 18:06, 18:06",
            "    171 building :done, 18:06, 18:08",
            "    171 review_wait :done, 18:08, 18:16",
            "    171 merged :18:16, 18:30",
            "```"]))

    def test_status_reads_while_the_store_holds_its_lock(self):
        self.st.put_job("171", "building", {}, at=at("18:00"))
        self.st.put_job("172", "queued", {"waiting": [171]}, at=at("18:05"))
        lines = T.status_lines(T.read_rows(self.path), T.parse(at("18:10")))
        self.assertEqual(lines[0], "#171 building for 10 min | pr - | no waits")
        self.assertEqual(lines[1], "#172 queued for 5 min | pr - | waits on #171 for 5 min")

    def test_end_states_listed_for_24_hours_and_crit_bars(self):
        self.st.put_job("1", "blocked", {}, reason="old", at="2026-11-10T10:00:00Z")
        self.st.put_job("2", "failed", {}, reason="boom", at=at("10:00"))
        self.st.put_job("3", "waiting", {}, at=at("10:00"))
        self.st.put_job("3", "waiting", {}, at=at("10:02"))
        rows = T.read_rows(self.path)
        now = T.parse(at("11:00"))
        lines = T.status_lines(rows, now)
        self.assertEqual(lines, ["#3 waiting for 60 min | pr - | no waits", "#2 failed: boom"])
        g = T.gantt(rows, now, now - 24 * 3600)
        self.assertIn("    2 failed :crit, 10:00, 11:00", g)
        self.assertIn("    3 waiting :crit, 10:00, 11:00", g)
        self.assertNotIn("section 1", g)


if __name__ == "__main__":
    unittest.main()
