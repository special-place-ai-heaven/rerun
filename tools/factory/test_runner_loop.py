"""runner_loop tests with a fake engine: end recorded in one tick, long run cancelled, one refire on error,
restart mid-job without a double fire."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runner_loop as R, store as S, limits as L

T0 = 1_800_000_000.0


class FakeEngine:
    def __init__(self):
        self.runs, self.fires, self.cancelled, self.n = {}, [], [], 0

    def list_triggers(self, agent):
        return [{"slug": "factory-challenge", "token": "tok-secret"}]

    def create_trigger(self, *a, **k):
        raise AssertionError("trigger exists")

    def fire_trigger(self, agent, slug, token, payload):
        self.n += 1
        rid = "run%d" % self.n
        self.fires.append((slug, payload))
        self.runs[rid] = {"id": rid, "status": "running", "startedAt": R.iso(self.now), "triggerSlug": slug}
        return rid, "s"

    def get_run(self, agent, rid):
        return self.runs.get(rid)

    def run_steps(self, agent, rid):
        return []

    def list_runs(self, agent, **k):
        return list(self.runs.values())

    def cancel(self, agent, rid):
        self.cancelled.append(rid)
        self.runs[rid]["status"] = "cancelled"
        return True


class TestRunner(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.cfg = {"poll_s": 30, "run_limit_s": 600, "stall_s": 0, "token_file": os.path.join(self.d.name, "tok.json"),
                    "store_file": os.path.join(self.d.name, "ledger.db"),
                    "triggers": [{"stage": "challenge", "coworker": "DA", "agent": "ag1", "slug": "factory-challenge"}]}
        self.eng = FakeEngine()
        self.now = T0
        self.eng.now = T0
        self.runner = self.make()

    def make(self):
        self.eng.now = self.now
        return R.build(self.cfg, self.eng, clock=lambda: self.now)

    def tearDown(self):
        self.runner.st.close()
        self.d.cleanup()

    def tick(self, dt=30):
        self.now += dt
        self.eng.now = self.now
        self.runner.tick()

    def fires(self):
        return self.runner.st.db.execute("SELECT * FROM fires ORDER BY id").fetchall()

    def test_done_recorded_within_one_tick(self):
        R.enqueue(self.runner.st, "60", "challenge", "C7")
        self.tick()
        self.assertEqual(len(self.eng.fires), 1)
        self.assertEqual(self.eng.fires[0][1]["job"], "60")
        self.assertEqual(self.fires()[0]["status"], "running")
        self.eng.runs["run1"].update(status="done", inputTokens=5, outputTokens=2)
        self.tick()
        f = self.fires()[0]
        self.assertEqual((f["status"], f["tokens_in"], f["tokens_out"]), ("done", 5, 2))
        self.assertIsNotNone(f["ended_at"])

    def test_long_run_cancelled(self):
        R.enqueue(self.runner.st, "60", "challenge")
        self.tick()
        self.tick(700)
        self.assertEqual(self.eng.cancelled, ["run1"])
        self.assertEqual(self.fires()[0]["status"], "cancelled")
        self.tick()
        self.assertEqual(len(self.eng.fires), 1)  # a cancel is not refired

    def test_error_refired_exactly_once(self):
        R.enqueue(self.runner.st, "60", "challenge")
        self.tick()
        self.eng.runs["run1"].update(status="error", error="boom")
        self.tick()
        self.assertEqual(len(self.eng.fires), 2)
        self.eng.runs["run2"].update(status="error", error="boom")
        self.tick()
        self.tick()
        self.assertEqual(len(self.eng.fires), 2)
        self.assertEqual([f["status"] for f in self.fires()], ["error", "failed"])

    def test_engine_restart_row_refired_once(self):
        R.enqueue(self.runner.st, "60", "challenge")
        self.tick()
        self.eng.runs["run1"].update(status="error", error=L.RESTARTED)
        self.tick()
        self.assertEqual(len(self.eng.fires), 2)

    def test_runner_restart_continues_without_double_fire(self):
        R.enqueue(self.runner.st, "60", "challenge")
        self.tick()
        self.runner.st.close()
        self.runner = self.make()  # new process: tokens from file, store from disk
        self.tick()
        self.assertEqual(len(self.eng.fires), 1)
        self.eng.runs["run1"].update(status="done")
        self.runner.st.close()
        self.runner = self.make()
        self.tick()
        self.assertEqual(len(self.eng.fires), 1)
        self.assertEqual(self.fires()[0]["status"], "done")

    def test_crash_between_intent_and_fire_resolved_not_refired(self):
        R.enqueue(self.runner.st, "60", "challenge")
        orig = self.eng.fire_trigger

        def lost(*a):
            orig(*a)  # the engine started the run, the answer was lost
            raise R.E.EngineError("timeout")
        self.eng.fire_trigger = lost
        self.tick()
        self.assertEqual(self.fires()[0]["status"], "intent")
        self.runner.st.close()
        self.eng.fire_trigger = orig
        self.runner = self.make()
        self.tick()
        self.assertEqual(len(self.eng.fires), 1)
        self.assertEqual(self.fires()[0]["run_id"], "run1")

    def test_enqueue_while_store_locked(self):
        R.enqueue_file(self.cfg["store_file"], "61", "challenge")
        self.assertEqual(len(R.queued(self.runner.st)), 1)


class SetupEngine:
    """In-memory dev engine for `setup`: counts every create."""
    def __init__(self):
        self.conns, self.agents, self.default, self.posts, self.triggers = [], [], None, [], {}
    def _call(self, method, path, query=None, payload=None):
        if method == "POST":
            self.posts.append(path)
        if (method, path) == ("GET", "/connections"):
            return {"connections": list(self.conns), "default": self.default}
        if (method, path) == ("POST", "/connections"):
            c = dict(payload, id="conn%d" % (len(self.conns) + 1))
            self.conns.append(c)
            return c
        if (method, path) == ("PUT", "/connections/default"):
            self.default = dict(payload)
            return self.default
        if (method, path) == ("GET", "/agents"):
            return {"agents": [{"id": a["id"], "name": a["config"]["name"]} for a in self.agents]}
        if (method, path) == ("POST", "/agents"):
            a = {"id": "ag-%s" % payload["config"]["name"], "config": payload["config"]}
            self.agents.append(a)
            return a
        raise AssertionError((method, path))
    def list_triggers(self, agent):
        return [t for (a, _), t in self.triggers.items() if a == agent]
    def create_trigger(self, agent, name, body, model=None, **k):
        self.posts.append("trigger")
        t = {"slug": name, "token": "tok-" + name, "model": model}
        self.triggers[(agent, name)] = t
        return t


class TestSetup(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        os.environ.pop("FACTORY_DATA_DIR", None)
        self.cfg = {"store_file": os.path.join(self.d.name, "ledger.db"),
                    "token_file": os.path.join(self.d.name, "tok.json"),
                    "triggers": [
                        {"stage": "challenge", "coworker": "DA", "agent_name": "challenge", "slug": "factory-challenge", "model": "stub-fast"},
                        {"stage": "challenge", "coworker": "DA", "agent_name": "challenge-hold", "slug": "factory-challenge-hold", "model": "stub-hold"}]}
    def tearDown(self):
        self.d.cleanup()
    def test_creates_then_second_run_creates_nothing(self):
        eng = SetupEngine()
        R.setup(eng, self.cfg)
        self.assertEqual(sorted(eng.posts), ["/agents", "/agents", "/connections", "trigger", "trigger"])
        self.assertEqual(eng.default, {"connectionId": "conn1", "model": "stub-fast"})
        self.assertEqual({a["config"]["name"]: a["config"]["model"] for a in eng.agents}, {"challenge": "stub-fast", "challenge-hold": "stub-hold"})
        state = R.read_state(self.cfg)
        self.assertEqual(state["agents"], {"challenge": "ag-challenge", "challenge-hold": "ag-challenge-hold"})
        self.assertTrue(state_path_in_volume(self.cfg, self.d.name))
        eng.posts.clear()
        out = R.setup(eng, self.cfg)
        self.assertEqual(eng.posts, [])
        self.assertTrue(all("created" not in l for l in out), out)
        self.assertEqual(R.read_state(self.cfg), state)
    def test_reuses_by_name_when_state_file_is_lost(self):
        eng = SetupEngine()
        R.setup(eng, self.cfg)
        os.unlink(R.state_path(self.cfg))
        eng.posts.clear()
        R.setup(eng, self.cfg)
        self.assertEqual(eng.posts, [])
        self.assertEqual(len(eng.agents), 2)
    def test_run_reads_ids_from_state_and_waits_without_it(self):
        with self.assertRaises(R.NeedsSetup):
            R.load_runtime(self.cfg)
        R.setup(SetupEngine(), self.cfg)
        rt = R.load_runtime(self.cfg)
        self.assertEqual([e["agent"] for e in rt["triggers"]], ["ag-challenge", "ag-challenge-hold"])
        self.assertNotIn("agent", self.cfg["triggers"][0])  # the template is not changed
    def test_store_path_default_is_the_data_dir_and_state_sits_beside_it(self):
        os.environ["FACTORY_DATA_DIR"] = "/vol"
        try:
            self.assertEqual(R.store_path({}), "/vol/ledger.db")
            self.assertEqual(R.state_path({}), "/vol/runner-state.json")
        finally:
            os.environ.pop("FACTORY_DATA_DIR")
    def test_shipped_runner_json_is_a_template_without_ids(self):
        import trigger as T
        for e in T.load_config()["triggers"]:
            self.assertNotIn("agent", e)
            self.assertTrue(e["agent_name"] and e["model"].startswith("stub-"))


def state_path_in_volume(cfg, d):
    return os.path.dirname(R.state_path(cfg)) == d == os.path.dirname(R.store_path(cfg))


if __name__ == "__main__":
    unittest.main()
