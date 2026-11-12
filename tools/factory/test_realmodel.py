#!/usr/bin/env python3
"""test_realmodel (rerun#71): the subscription connection and the one-run proof against a fake engine object.
The token must reach the engine in one request body and appear nowhere else."""
import contextlib, io, os, sys, unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
import realmodel as R

TOKEN = "sk-ant-oat01-" + "Ab3_" * 12
CONN = {"id": "c1", "name": "claude-plan", "provider": "claude"}
STUB = {"id": "s1", "name": "stub", "provider": "custom"}
DONE = {"status": "done", "provider": "claude", "model": "claude-haiku-5-5", "inputTokens": 9100, "outputTokens": 4}


class FakeEng:
    def __init__(self, connections=(), default="s1", rows=(DONE,), fire_error=None):
        self.calls, self.connections, self.default = [], list(connections), default
        self.rows, self.fire_error = list(rows), fire_error

    def _call(self, method, path, query=None, payload=None):
        self.calls.append((method, path, payload))
        if (method, path) == ("GET", "/connections"):
            return {"connections": list(self.connections), "default": {"connectionId": self.default}}
        if (method, path) == ("POST", "/connections"):
            self.connections.append(dict(CONN))
            return dict(CONN)
        if (method, path) == ("POST", "/agents"):
            return {"id": "a1"}
        return {}

    def create_trigger(self, agent_id, name, body):
        self.calls.append(("TRIGGER", agent_id, body))
        return {"slug": "probe", "token": "trigger-token"}

    def fire_trigger(self, agent_id, slug, token, payload):
        if self.fire_error:
            raise self.fire_error
        return "r1", "s1"

    def get_run(self, agent_id, run_id):
        return self.rows.pop(0) if len(self.rows) > 1 else self.rows[0]


def everything(eng, out=()):
    return repr([(m, p) for m, p, _ in eng.calls]) + "\n".join(out)


class Connect(unittest.TestCase):
    def test_bad_token_is_refused_and_nothing_is_sent(self):
        for bad in ("", "short", "has a space " + "x" * 30, 'quote"' + "x" * 30, "line\nbreak" + "x" * 30):
            eng = FakeEng([STUB])
            with self.assertRaises(ValueError):
                R.connect(eng, bad)
            self.assertEqual(eng.calls, [])

    def test_creates_a_claude_connection_with_the_token_only_in_the_body(self):
        eng = FakeEng([STUB])
        out = R.connect(eng, TOKEN + "\n")
        posts = [c for c in eng.calls if c[0] == "POST"]
        self.assertEqual(posts, [("POST", "/connections", {"name": "claude-plan", "provider": "claude", "keys": {"CLAUDE_CODE_OAUTH_TOKEN": TOKEN}})])
        self.assertEqual(out, ["connection=created", "connection=present default-is-real-model=no"])
        self.assertNotIn(TOKEN, everything(eng, out))

    def test_an_existing_connection_gets_the_new_token(self):
        eng = FakeEng([STUB, CONN])
        self.assertEqual(R.connect(eng, TOKEN), ["connection=updated"])
        self.assertIn(("PATCH", "/connections/c1/keys", {"set": {"CLAUDE_CODE_OAUTH_TOKEN": TOKEN}}), eng.calls)

    def test_check_says_when_the_real_model_became_the_default(self):
        self.assertEqual(R.check(FakeEng([STUB])), ["connection=absent default-is-real-model=no"])
        self.assertEqual(R.check(FakeEng([CONN], default="c1")), ["connection=present default-is-real-model=yes"])


class Probe(unittest.TestCase):
    def test_one_run_on_the_real_model_and_the_coworker_is_removed(self):
        eng = FakeEng([STUB, CONN], rows=[{"status": "running"}, DONE])
        out = R.probe(eng, sleep=lambda s: None)
        self.assertEqual(out, ["run=r1 status=done provider=claude model=claude-haiku-5-5 input-tokens=9100 output-tokens=4"])
        cfg = next(p for m, path, p in eng.calls if (m, path) == ("POST", "/agents"))["config"]
        self.assertEqual((cfg["connectionId"], cfg["provider"], cfg["model"]), ("c1", "claude", "claude-haiku-5-5"))
        self.assertEqual(eng.calls[-1][:2], ("DELETE", "/agents/a1"))

    def test_coworker_is_removed_when_the_fire_fails(self):
        eng = FakeEng([CONN], fire_error=E.EngineError("engine answered HTTP 500 for POST /agents/a1/triggers/probe/fire"))
        with self.assertRaises(E.EngineError):
            R.probe(eng, sleep=lambda s: None)
        self.assertEqual(eng.calls[-1][:2], ("DELETE", "/agents/a1"))

    def test_a_credential_in_an_error_text_is_cut(self):
        eng = FakeEng([CONN], rows=[{"status": "error", "error": "provider refused " + TOKEN + " for this plan"}])
        out = R.probe(eng, sleep=lambda s: None)[0]
        self.assertIn("status=error", out)
        self.assertIn("error=provider refused <cut> for this plan", out)
        self.assertNotIn(TOKEN, out)

    def test_no_connection_no_coworker(self):
        eng = FakeEng([STUB])
        with self.assertRaises(RuntimeError):
            R.probe(eng)
        self.assertEqual([c for c in eng.calls if c[0] != "GET"], [])


class Main(unittest.TestCase):
    def test_a_failed_connect_prints_no_token(self):
        class Refusing(FakeEng):
            def _call(self, method, path, query=None, payload=None):
                if method == "POST":
                    raise E.EngineError("engine answered HTTP 400 for POST /connections")
                return super()._call(method, path, query, payload)
        buf = io.StringIO()
        with mock.patch.object(E, "Engine", lambda: Refusing([STUB])), contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = R.main(["connect"], stdin=io.StringIO(TOKEN + "\n"))
        self.assertEqual(code, 1)
        self.assertIn("realmodel connect failed: engine answered HTTP 400", buf.getvalue())
        self.assertNotIn(TOKEN, buf.getvalue())

    def test_remove_and_usage(self):
        eng = FakeEng([STUB, CONN])
        self.assertEqual(R.remove(eng), ["connection=removed"])
        self.assertEqual(eng.calls[-1][:2], ("DELETE", "/connections/c1"))
        with mock.patch.object(E, "Engine", lambda: FakeEng()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(R.main(["nonsense"]), 2)


if __name__ == "__main__":
    unittest.main()
