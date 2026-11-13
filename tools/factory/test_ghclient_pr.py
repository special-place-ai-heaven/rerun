import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghclient


class Stub(ghclient.Client):
    def __init__(self, pulls):
        super().__init__("http://x", "o/r")
        self.pulls, self.sent = pulls, []

    def req(self, method, path, body=None):
        self.sent.append((method, path, body))
        if path.startswith("/git/ref/"):
            return {"object": {"sha": "f00d"}}
        return self.pulls if method == "GET" else {"number": 9, "state": "open"}


def pr(n, state="open", merged_at=None, sha=None):
    return {"number": n, "state": state, "merged_at": merged_at, "merge_commit_sha": sha}


class GhPr(unittest.TestCase):
    def test_pr_by_head_none_when_absent(self):
        c = Stub([])
        self.assertIsNone(c.pr_by_head("b/x"))
        self.assertIn("head=o%3Ab%2Fx", c.sent[0][1])

    def test_pr_by_head_reports_merge(self):
        got = Stub([pr(4, "closed", "2026-01-01", "abc")]).pr_by_head("b")
        self.assertEqual(got, {"number": 4, "state": "closed", "merged": True, "merge_sha": "abc"})
        got = Stub([pr(5, "closed")]).pr_by_head("b")
        self.assertEqual((got["merged"], got["merge_sha"]), (False, None))

    def test_open_pr_reuses_existing_pr_for_head(self):
        c = Stub([pr(4, "closed"), pr(7)])
        self.assertEqual(c.open_pr("t", "b", "dev", body="B")["number"], 7)
        self.assertEqual([s[0] for s in c.sent], ["GET"])

    def test_open_pr_creates_with_body_when_none_open(self):
        c = Stub([pr(4, "closed", "m", "s")])
        self.assertEqual(c.open_pr("t", "b", "dev", body="B")["number"], 9)
        self.assertEqual(c.sent[-1], ("POST", "/pulls", {"title": "t", "head": "b", "base": "dev", "body": "B"}))

    def test_branch_sha_reads_ref(self):
        c = Stub([])
        self.assertEqual(c.branch_sha("wave/x"), "f00d")
        self.assertEqual(c.sent[0][:2], ("GET", "/git/ref/heads/wave/x"))


if __name__ == "__main__":
    unittest.main()
