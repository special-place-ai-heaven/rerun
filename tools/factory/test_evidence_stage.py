import unittest

import evidence as E

FULL = "o/r"
KV = {"repo_url": "https://github.com/o/r.git", "test:A1": "factory tools/factory/test_a.py"}
READY = {"paths": ["tools/factory/a.py", "tools/factory/test_a.py"]}
F = {"job": "71", "chunk": "A1", "stage": "build", "intent_at": "2026-11-12T08:00:00Z"}
REFS = "repos/o/r/git/matching-refs/heads/chunk/71-A1"
CMP = "repos/o/r/compare/job/71...chunk/71-A1"


def fake(data):
    return lambda path, paginate=False: data[path]


class EvidenceStage(unittest.TestCase):
    def test_build_run_without_pushed_branch_is_none(self):
        self.assertEqual(E.stage_check(fake({REFS: []}), F, KV, READY), ("NONE", "chunk/71-A1 was not pushed"))

    def test_pushed_branch_with_test_and_paths_is_ok(self):
        data = {REFS: [{"ref": "refs/heads/chunk/71-A1", "object": {"sha": "c9"}}],
                CMP: {"commits": [{"commit": {"committer": {"date": "2026-11-12T09:00:00Z"}}}],
                      "files": [{"filename": "tools/factory/a.py", "additions": 3, "deletions": 0},
                                {"filename": "tools/factory/test_a.py", "additions": 5, "deletions": 0}]}}
        v, d = E.stage_check(fake(data), F, KV, READY)
        self.assertEqual((v, d["sha"], d["lines"]), ("OK", "c9", 8))

    def test_other_stage_needs_no_evidence(self):
        self.assertEqual(E.stage_check(fake({}), dict(F, stage="review"), KV, READY), ("OK", ""))


if __name__ == "__main__":
    unittest.main()
