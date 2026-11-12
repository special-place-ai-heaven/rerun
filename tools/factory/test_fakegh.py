"""fakegh.py tests: the local fake serves what the client needs and records every call."""
import json, os, sys, unittest, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakegh


def call(url, method="GET", body=None):
    req = urllib.request.Request(url, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": "token t"})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read()), r.headers


class Fakegh(unittest.TestCase):
    def setUp(self):
        self.f = fakegh.Fake(issues={71: {"number": 71, "title": "m3"}}, comments={71: [{"id": i} for i in range(5)]},
                             commits={"abc": {"sha": "abc"}}, statuses={"abc": [{"state": "success"}]},
                             checks={"abc": {"check_runs": [{"name": "ci"}]}})
        self.f.start()
        self.u = self.f.url + "/repos/o/r"

    def tearDown(self):
        self.f.stop()

    def test_serves_issue_and_records_calls(self):
        st, body, _ = call(self.u + "/issues/71")
        self.assertEqual((st, body["title"]), (200, "m3"))
        self.assertEqual(self.f.calls[-1][:2], ("GET", "/repos/o/r/issues/71"))
        self.assertEqual(call(self.u + "/commits/abc")[1]["sha"], "abc")
        self.assertEqual(call(self.u + "/commits/abc/status")[1][0]["state"], "success")
        self.assertEqual(call(self.u + "/commits/abc/check-runs")[1]["check_runs"][0]["name"], "ci")

    def test_pagination_link_header(self):
        _, p1, h = call(self.u + "/issues/71/comments?per_page=2")
        self.assertEqual(len(p1), 2)
        self.assertIn('rel="next"', h["Link"])
        _, p3, h = call(self.u + "/issues/71/comments?per_page=2&page=3")
        self.assertEqual((len(p3), h["Link"]), (1, None))

    def test_creates_issue_and_pr(self):
        st, i, _ = call(self.u + "/issues", "POST", {"title": "x"})
        self.assertEqual((st, i["number"]), (201, 72))
        st, pr, _ = call(self.u + "/pulls", "POST", {"head": "b", "base": "dev"})
        self.assertEqual(st, 201)
        self.assertEqual(self.f.calls[-1][2], {"head": "b", "base": "dev"})


if __name__ == "__main__":
    unittest.main()
