import json, os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class Settings(unittest.TestCase):
    def test_values_as_ruled(self):
        with open(os.path.join(HERE, "runner.json")) as f:
            cfg = json.load(f)
        self.assertEqual(cfg["token_cap"], 400000)
        self.assertEqual(cfg["builder_capacity"], 3)
        self.assertEqual(cfg["per_job_cap"], 2)
        self.assertEqual(cfg["retries"], 1)
        self.assertEqual(sorted(cfg["model_tiers"]), ["large", "mid", "small"])


if __name__ == "__main__":
    unittest.main()
