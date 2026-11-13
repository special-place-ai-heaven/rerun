import unittest

import pools


def cw(*ids):
    return [{"id": i, "name": i.upper()} for i in ids]


class Pools(unittest.TestCase):
    def test_the_old_keys_and_a_types_map_give_the_same_types_and_picks(self):
        old = {"builders": cw("b1", "b2"), "reviewers": cw("r1", "r2"), "max_jobs": 8}
        new = {"types": {"coder": {"coworkers": cw("b1", "b2"), "max_jobs": 8},
                         "reviewer": {"coworkers": cw("r1", "r2")}}}
        self.assertEqual(pools.types(old), pools.types(new))
        self.assertEqual(pools.names(old), pools.names(new))
        self.assertEqual(len(pools.names(old)), 4)
        for cfg in (old, new):
            self.assertEqual(pools.pick(cfg, "coder", {"b1"}), "b2")
            self.assertIsNone(pools.pick(cfg, "coder", {"b1", "b2"}))
            self.assertEqual(pools.pick(cfg, "reviewer", set()), "r1")
            self.assertIsNone(pools.pick(cfg, "designer", set()))
            self.assertEqual(pools.max_jobs(cfg, "coder"), 8)
            self.assertIsNone(pools.max_jobs(cfg, "reviewer"))
            self.assertIsNone(pools.max_jobs(cfg, "designer"))
            for t in pools.types(cfg).values():
                self.assertTrue(all(c["runs"] == 1 for c in t["coworkers"]))

    def test_old_keys_default_max_jobs_is_8(self):
        self.assertEqual(pools.max_jobs({"builders": cw("b1")}, "coder"), 8)


if __name__ == "__main__":
    unittest.main()
