import unittest

import intake

OK1 = "- [ ] A1. First | builder: code | test: factory tools/factory/test_a.py | done-test: test_a::A::one | paths: tools/factory/a.py, tools/factory/test_a.py | max-lines: 80 | depends on: -"
OK2 = OK1.replace("A1.", "A2.").replace("First", "Second")
BAD = "- [ ] A3. Third | builder: code | test: factory tools/factory/test_c.py | done-test: one | paths: tools/factory/c.py | max-lines: 80 | depends on: -"


def plan(*lines, marker="PLAN READY"):
    return "%s\n\nGoal\n\n## Chunks\n### Wave 1\n%s\n## Other\n%s\n" % (marker, "\n".join(lines), OK1.replace("A1.", "Z9."))


class Intake(unittest.TestCase):
    def test_three_lines_ok_bad_rejected(self):
        chunks, errors = intake.parse_plan(plan(OK1, OK2, BAD))
        self.assertEqual([c["id"] for c in chunks], ["A1", "A2"])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("A3: "))

    def test_no_marker_or_no_chunks(self):
        self.assertEqual(intake.parse_plan(plan(OK1, marker="hello")), ([], ["no PLAN READY marker"]))
        self.assertEqual(intake.parse_plan("PLAN READY\nnothing"), ([], ["no chunk lines under ## Chunks"]))

    def test_duplicate_id(self):
        chunks, errors = intake.parse_plan(plan(OK1, OK1))
        self.assertEqual(len(chunks), 1)
        self.assertIn("duplicate", errors[0])


if __name__ == "__main__":
    unittest.main()
