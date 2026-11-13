import unittest

import briefs


class Briefs(unittest.TestCase):
    J = {"issue": 7, "title": "Note x", "extra": "PLAN."}

    def test_each_brief_names_the_job_its_files_and_one_pull_request(self):
        r = briefs.research_brief(self.J)
        d = briefs.design_brief(self.J)
        for b in (r, d):
            for s in ("rerun #7", "Note x", "(#7)", "Closes #7",
                      "one pull request into dev", "special-place-administrator",
                      "call no other coworker", "BLOCKED: plan:",
                      "issue number in its name",
                      "/data/tools/bin/pr-open --template"):
                self.assertIn(s, b)
            self.assertNotIn("Final state", b)
        for s in ("source", "date", "/data/tools/bin/wt new rerun 7 r1"):
            self.assertIn(s, r)
        for s in ("options", "/data/tools/bin/wt new rerun 7 d1"):
            self.assertIn(s, d)


if __name__ == "__main__":
    unittest.main()
