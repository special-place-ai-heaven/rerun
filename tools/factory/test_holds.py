import os, tempfile, unittest

import holds, store

T = 1_000_000


class Holds(unittest.TestCase):
    def test_a_hold_survives_a_restart_ends_on_its_time_and_plan_limit_comes_first(self):
        self.assertEqual(holds.PLAN_LIMIT_HOLD_S, 1800)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "ledger.db")
            st = store.Store(path)
            holds.arm(st, "plan limit", T + 1800)
            st.close()
            st = store.Store(path)
            self.assertEqual(holds.active(st, T + 10), {"kind": "plan limit", "until": T + 1800})
            self.assertIsNone(holds.active(st, T + 1800))
            holds.arm(st, "plan limit", T + 600)
            holds.arm(st, "sign-in renewal", T + 600)
            self.assertEqual(holds.active(st, T)["kind"], "plan limit")
            holds.clear(st, "plan limit")
            self.assertEqual(holds.active(st, T), {"kind": "sign-in renewal", "until": T + 600})
            st.close()


if __name__ == "__main__":
    unittest.main()
