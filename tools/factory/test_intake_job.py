import os, tempfile, unittest

import intake
import store
from test_intake import OK1, OK2, plan

OK3 = OK1.replace("A1.", "A3.").replace("First", "Third") .replace("depends on: -", "depends on: A1, A2")


class IntakeJob(unittest.TestCase):
    def test_three_lines_three_ready_items(self):
        with tempfile.TemporaryDirectory() as d:
            st = store.Store(os.path.join(d, "s.db"))
            state, errors = intake.register(st, "71", plan(OK1, OK2, OK3))
            self.assertEqual(errors, [])
            self.assertEqual(state["job_branch"], "job/71")
            self.assertEqual(state["chunks"], {"A1": "PENDING", "A2": "PENDING", "A3": "PENDING"})
            self.assertEqual([r["chunk"] for r in st.ready_list("71")], ["A1", "A2", "A3"])
            self.assertEqual(st.get_ready("71", "A3")["deps"], ["A1", "A2"])
            self.assertEqual([(q["stage"], q["chunk"]) for q in st.queued()], [("challenge", "")])
            st.close()

    def test_no_valid_chunk_stores_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            st = store.Store(os.path.join(d, "s.db"))
            self.assertEqual(intake.register(st, "71", "hello")[0], None)
            self.assertEqual((st.ready_list(), st.queued()), ([], []))
            st.close()


if __name__ == "__main__":
    unittest.main()
