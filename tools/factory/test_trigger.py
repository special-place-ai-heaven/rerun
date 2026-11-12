"""trigger.py tests: the HTTP call, the env file and system.db are faked or temp files; nothing touches the network or /data."""
import contextlib, io, json, os, shutil, sqlite3, sys, tempfile, unittest, urllib.error
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trigger as T

TOKEN = "tok-SECRET-0123456789abcdef"
URL = "https://rerun.example/api/t/agent-da/factory-challenge/" + TOKEN


class Answer:
    def __init__(self, status, body):
        self.status, self.body = status, body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trigger-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, rel, text):
        p = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return p

    def main(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = T.main(argv)
        self.assertNotIn(TOKEN, out.getvalue() + err.getvalue())
        return code, out.getvalue()


class TestFire(unittest.TestCase):
    def test_fire_ok(self):
        sent = []

        def opener(req, timeout):
            sent.append(req)
            return Answer(202, b'{"runId":"run-1","sessionId":"ses-1","triggerSlug":"factory-challenge"}')
        self.assertEqual(T.fire(URL, {"v": 1, "stage": "probe"}, urlopen=opener), ("run-1", "ses-1"))
        self.assertEqual(len(sent), 1)
        self.assertEqual((sent[0].get_method(), sent[0].full_url, sent[0].data), ("POST", URL, b'{"v":1,"stage":"probe"}'))
        self.assertEqual(sent[0].get_header("Content-type"), "application/json")

    def test_errors_never_show_url_or_token(self):
        def raising(e):
            def opener(req, timeout):
                raise e
            return opener
        cases = [raising(urllib.error.HTTPError(URL, 404, "not found " + TOKEN, {}, None)),
                 raising(urllib.error.URLError("cannot reach " + URL)),
                 raising(ValueError("unknown url type: " + URL)),
                 lambda req, timeout: Answer(200, json.dumps({"error": TOKEN}).encode()),
                 lambda req, timeout: Answer(202, b"not json " + TOKEN.encode())]
        for opener in cases:
            with self.assertRaises(T.TriggerError) as cm:
                T.fire(URL, {"v": 1}, urlopen=opener)
            self.assertNotIn(TOKEN, str(cm.exception))
            self.assertNotIn("example", str(cm.exception))
            self.assertTrue(cm.exception.__suppress_context__ or cm.exception.__context__ is None)

    def test_one_call_only_on_timeout(self):
        calls = []

        def opener(req, timeout):
            calls.append(1)
            raise TimeoutError("timed out")
        with self.assertRaises(T.TriggerError):
            T.fire(URL, {}, urlopen=opener)
        self.assertEqual(len(calls), 1)  # a timeout may still have started a run: never fired twice

    def test_url_from_env_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "runner.env")
            with open(p, "w", newline="\n") as f:
                f.write("# urls\nFACTORY_TRIGGER_PLAN_ADA=https://x/a\nFACTORY_TRIGGER_CHALLENGE_DEVILS_ADVOCATE=\"%s\"\n" % URL)
            self.assertEqual(T.trigger_url("challenge", "devils_advocate", p), URL)
            with self.assertRaises(T.TriggerError) as cm:
                T.trigger_url("build", "larry", p)
            self.assertIn("FACTORY_TRIGGER_BUILD_LARRY", str(cm.exception))
            self.assertNotIn(TOKEN, str(cm.exception))


class TestRunReader(TempDir):
    def db(self, cols):
        p = os.path.join(self.tmp, "system.db")
        con = sqlite3.connect(p)
        con.execute("CREATE TABLE runs (%s)" % ", ".join(cols))
        return p, con

    def test_reads_row_by_id(self):
        p, con = self.db(["id TEXT PRIMARY KEY", "agent_id TEXT", "session_id TEXT", "status TEXT", "usage_json TEXT", "started_at TEXT",
                          "finished_at TEXT", "error TEXT", "input_tokens INTEGER", "trigger_source TEXT", "trigger_slug TEXT"])
        con.execute("INSERT INTO runs VALUES ('r1','a','s1','done','{}','2026-11-12T08:00:00.123Z','2026-11-12T08:03:00.000Z',NULL,812,'trigger','factory-challenge')")
        con.commit()
        con.close()
        row = T.read_run("a", "r1", p)
        self.assertEqual((row["status"], row["input_tokens"], row["trigger_slug"], row["session_id"]), ("done", 812, "factory-challenge", "s1"))
        self.assertEqual(T.input_tokens(row), 812)
        self.assertIsNone(T.read_run("a", "other", p))

    def test_missing_columns_read_as_null(self):
        p, con = self.db(["id TEXT", "session_id TEXT", "status TEXT", "usage_json TEXT", "started_at TEXT"])
        con.execute("INSERT INTO runs VALUES ('r1','s1','done','{\"inputTokens\": 9000}','2026-11-12T08:00:00.000Z')")
        con.commit()
        con.close()
        row = T.read_run("a", "r1", p)
        self.assertIsNone(row["input_tokens"])
        self.assertIsNone(row["trigger_slug"])
        self.assertEqual(T.input_tokens(row), 9000)
        self.assertIsNone(T.input_tokens({"usage_json": None}))

    def test_read_only_never_creates_the_file(self):
        p = os.path.join(self.tmp, "absent", "system.db")
        with self.assertRaises(sqlite3.Error):
            T.read_run("a", "r1", p)
        self.assertFalse(os.path.exists(p))

    def test_default_path_is_the_agent_data_dir(self):
        self.assertEqual(T.db_path("ag1").replace("\\", "/"), T.AGENTS.replace("\\", "/") + "/ag1/data/system.db")


class TestCheckTriggers(TempDir):
    BODY = "You were started by the factory runner.\nDo the challenge.\n"

    def setUp(self):
        super().setUp()
        self.cfg = self.write("runner.json", json.dumps({"tick_seconds": 120, "triggers": [
            {"stage": "challenge", "coworker": "DEVILS_ADVOCATE", "agent": "agent-da", "slug": "factory-challenge", "model": "claude-x"}]}))
        self.write("triggers/challenge.md", self.BODY)
        for k, v in (("CONFIG", self.cfg), ("TRIGGERS", os.path.join(self.tmp, "triggers")), ("AGENTS", os.path.join(self.tmp, "agents"))):
            p = mock.patch.object(T, k, v)
            p.start()
            self.addCleanup(p.stop)

    def live(self, body, model="claude-x"):
        front = "---\nname: factory-challenge\nenabled: true\ntoken: %s\nmethods:\n  - POST\nmodel: %s\n---\n" % (TOKEN, model)
        self.write("agents/agent-da/triggers/factory-challenge.md", front + "\n" + body + "\n")

    def test_same_body_and_model_is_ok(self):
        self.live(self.BODY.strip())
        self.assertEqual(self.main(["check-triggers"]), (0, "factory-challenge OK\n"))

    def test_drift_prints_slug_only(self):
        for body, model in ((self.BODY + "extra line", "claude-x"), (self.BODY, "claude-y"), (self.BODY, "null")):
            self.live(body, model)
            self.assertEqual(self.main(["check-triggers"]), (1, "factory-challenge DRIFT\n"))

    def test_missing_or_bad_live_file_is_drift(self):
        self.assertEqual(self.main(["check-triggers"]), (1, "factory-challenge DRIFT\n"))
        self.write("agents/agent-da/triggers/factory-challenge.md", "---\ntoken: %s\n%s" % (TOKEN, self.BODY))  # front matter never closed
        self.assertEqual(self.main(["check-triggers"]), (1, "factory-challenge DRIFT\n"))

    def test_front_matter_split(self):
        front, body = T.split_front("---\r\ntoken: x\r\nmodel: 'm-1'\r\n---\r\n\r\n  hello\r\n")
        self.assertEqual((T.model_of(front), body), ("m-1", "hello"))
        self.assertIsNone(T.model_of(["model: null"]))
        self.assertEqual(T.split_front("no front\n"), ([], "no front"))


class TestProbe(TempDir):
    def setUp(self):
        super().setUp()
        cfg = self.write("runner.json", json.dumps({"triggers": [
            {"stage": "challenge", "coworker": "DEVILS_ADVOCATE", "agent": "agent-da", "slug": "factory-challenge", "model": None}]}))
        env = self.write("runner.env", "FACTORY_TRIGGER_CHALLENGE_DEVILS_ADVOCATE=%s\n" % URL)
        for k, v in (("CONFIG", cfg), ("ENV", env), ("PROBE_POLL_S", 0)):
            p = mock.patch.object(T, k, v)
            p.start()
            self.addCleanup(p.stop)
        self.fired = []

    def probe(self, rows, wait=600):
        rows = list(rows)

        def fake_fire(url, payload, urlopen=None):
            self.fired.append((url, payload))
            return "run-1", "ses-1"
        with mock.patch.object(T, "fire", fake_fire), mock.patch.object(T, "PROBE_WAIT_S", wait), \
                mock.patch.object(T, "read_run", lambda agent, rid, path=None: rows.pop(0) if len(rows) > 1 else rows[0]):
            return self.main(["probe", "--stage", "challenge"])

    def test_done_under_limit_is_ok(self):
        code, out = self.probe([{"status": "running"}, {"status": "done", "input_tokens": 812}])
        self.assertEqual((code, out), (0, "PROBE OK run-1 ses-1 input=812\n"))
        self.assertEqual(self.fired, [(URL, {"v": 1, "stage": "probe"})])

    def test_too_many_tokens_error_or_still_running_fails(self):
        for rows, wait in (([{"status": "done", "input_tokens": 300000}], 600), ([{"status": "error", "input_tokens": 5}], 600),
                           ([{"status": "running"}], 0), ([None], 0)):
            code, out = self.probe(rows, wait)
            self.assertEqual(code, 1, out)
            self.assertTrue(out.startswith("PROBE FAIL run-1 ses-1"), out)

    def test_fire_error_and_unreadable_db_fail_without_token(self):
        def bad_fire(url, payload, urlopen=None):
            raise T.TriggerError("trigger answered HTTP 404")
        with mock.patch.object(T, "fire", bad_fire):
            self.assertEqual(self.main(["probe", "--stage", "challenge"]), (1, "PROBE FAIL: trigger answered HTTP 404\n"))

        def bad_db(agent, rid, path=None):
            raise sqlite3.OperationalError("unable to open database file")
        with mock.patch.object(T, "fire", lambda *a, **k: ("run-1", "ses-1")), mock.patch.object(T, "read_run", bad_db):
            code, out = self.main(["probe", "--stage", "challenge"])
        self.assertEqual(code, 1)
        self.assertIn("unable to open database file", out)

    def test_unknown_stage_refused(self):
        self.assertEqual(self.main(["probe", "--stage", "build"])[0], 2)


class TestFiles(unittest.TestCase):
    PREAMBLE = ("You were started by the factory runner. Your packet is the JSON in trigger_payload. Do only this stage, then end. "
                "Never wait for CI, never dispatch another coworker, never merge. If stage is `probe`: change nothing, post nothing, "
                "answer with the single line PROBE OK and end.")

    def test_challenge_body_and_runner_json(self):
        with open(os.path.join(T.HERE, "triggers", "challenge.md"), encoding="utf-8") as f:
            body = f.read()
        self.assertTrue(body.startswith(self.PREAMBLE))
        self.assertIn("`PLAN READY`", body)
        self.assertIn("`PLAN REJECT: <n> points open`", body)
        cfg = T.load_config()
        self.assertEqual(cfg["tick_seconds"], 120)
        self.assertIn(("challenge", "DEVILS_ADVOCATE", "factory-challenge"), [(e["stage"], e["coworker"], e["slug"]) for e in cfg["triggers"]])


if __name__ == "__main__":
    unittest.main()
