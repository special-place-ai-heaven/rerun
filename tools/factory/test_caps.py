import unittest
import limits


class Caps(unittest.TestCase):
    def test_batch_of_3_capped_at_strictest(self):
        cfg = {"token_cap": 500000}
        self.assertEqual(limits.chunk_cap(cfg), 400000)
        self.assertEqual(limits.chunk_cap({"token_cap": 300000}, {"token_cap": 900000}), 300000)
        self.assertEqual(limits.chunk_cap(cfg, {"token_cap": 200000}, 250000), 200000)
        self.assertEqual(limits.batch_cap(cfg, 3), 1200000)
        self.assertEqual(limits.stage_cfg({"token_cap": 400000}, {"token_cap": 900000})["token_cap"], 400000)


if __name__ == "__main__":
    unittest.main()
