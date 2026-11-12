import os, tempfile, unittest

import trigger as T


class FakeEngine:
    """Creates triggers without keeping the model (as the real create route does); PATCH keeps it."""
    def __init__(self, patch=True):
        self.patch, self.calls = patch, []

    def list_triggers(self, agent):
        return []

    def create_trigger(self, agent, name, body, model=None, **kw):
        self.calls.append(("create", model))
        return {"slug": name, "token": "tok", "model": None}

    def _call(self, method, path, query=None, payload=None):
        self.calls.append((method, path, payload))
        return {"model": payload["model"]} if self.patch else {}


class TriggerModel(unittest.TestCase):
    def cfg(self, d):
        return {"token_file": os.path.join(d, "t.json"), "triggers": [
            {"stage": "challenge", "agent": "ag", "slug": "factory-challenge", "model": "claude-x"}]}

    def test_fake_engine_gets_model(self):
        with tempfile.TemporaryDirectory() as d:
            eng = FakeEngine()
            T.ensure_triggers(eng, self.cfg(d))
            with open(os.path.join(d, "t.json"), encoding="utf-8") as f:
                self.assertIn("ag/factory-challenge", f.read())
        self.assertEqual(eng.calls[1], ("PATCH", "/agents/ag/triggers/factory-challenge", {"model": "claude-x"}))

    def test_model_not_taken_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(T.TriggerError):
                T.ensure_triggers(FakeEngine(patch=False), self.cfg(d))


if __name__ == "__main__":
    unittest.main()
