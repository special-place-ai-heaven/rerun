import os, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dispatch as D
from test_dispatch import World, PR_LINE


def run(extra):
    """One labelled issue to its review; returns the agents of the sends in order."""
    with tempfile.TemporaryDirectory() as d:
        w = World()
        cfg = {"repo": "o/r", "label": "factory", "checks_timeout_s": 3600, "auto_plan_marker": True,
               "ledger_file": os.path.join(d, "ledger.db"), "json_state_file": os.path.join(d, "dispatch.json"),
               "heartbeat_file": os.path.join(d, "heartbeat")}
        cfg.update(extra)
        w.ledger = cfg["ledger_file"]
        disp = D.Dispatcher(cfg, w.account, w.gh, now=lambda: w.clock)
        try:
            disp.once()
            w.finish("b1", PR_LINE)
            disp.once()
            disp.once()
        finally:
            disp.close()
        return [s[0] for s in w.sends]


class Types(unittest.TestCase):
    def test_the_shipped_settings_carry_the_same_coworkers_as_types_with_one_run_each(self):
        cfg = D.settings()
        for k in ("builders", "reviewers", "max_jobs"):
            self.assertNotIn(k, cfg)
        coder, rev = cfg["types"]["coder"], cfg["types"]["reviewer"]
        self.assertEqual([c["name"] for c in coder["coworkers"]], ["LARRY", "HOPPER", "code", "MARTIN", "BRENDAN"])
        self.assertEqual([c["name"] for c in rev["coworkers"]], ["LINUS", "BRUCE", "KENT", "FRED", "BARBARA"])
        ids = [c["id"] for c in coder["coworkers"] + rev["coworkers"]]
        self.assertTrue(all(ids))
        self.assertEqual(len(set(ids)), 10)
        self.assertTrue(all(c["runs"] == 1 for c in coder["coworkers"] + rev["coworkers"]))
        self.assertEqual(coder["max_jobs"], 8)

    def test_a_types_map_sends_the_build_and_the_review_to_the_first_free_coworker_of_the_type(self):
        def cw(ids):
            return [{"id": i, "name": i.upper(), "runs": 1} for i in ids]
        new = run({"types": {"coder": {"max_jobs": 8, "coworkers": cw(["b1", "b2"])}, "reviewer": {"coworkers": cw(["r1", "r2"])}}})
        old = run({"max_jobs": 8, "builders": [{"id": i, "name": i.upper()} for i in ("b1", "b2")],
                   "reviewers": [{"id": i, "name": i.upper()} for i in ("r1", "r2")]})
        self.assertEqual(new, ["b1", "r1"])
        self.assertEqual(new, old)


if __name__ == "__main__":
    unittest.main()
