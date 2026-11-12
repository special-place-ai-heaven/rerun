import unittest
import limits

TIERS = {"model_tiers": {"small": "s", "mid": "m", "large": "l"}}


class ModelRule(unittest.TestCase):
    def test_tier_by_stage(self):
        for st, want in (("checks", "s"), ("ci", "s"), ("gate", "s"), ("risk", "s"), ("build", "m"), ("fix", "m"),
                         ("plan", "l"), ("challenge", "l"), ("review", "l"), ("ruling", "l"), ("accept", "l")):
            self.assertEqual(limits.model_for(st, TIERS), want, st)
        self.assertEqual(limits.model_for("build"), "stub-mid")
        with self.assertRaises(ValueError):
            limits.model_for("lunch", TIERS)


if __name__ == "__main__":
    unittest.main()
