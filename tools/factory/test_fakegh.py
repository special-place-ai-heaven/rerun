import json, os, sys, unittest, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakegh


class Fakegh(unittest.TestCase):
    def test_serves_issue_and_records_calls(self):
        f = fakegh.Fake(issues={71: {"title": "m3"}}, comments={71: [{}] * 3})
        f.start()
        self.addCleanup(f.stop)
        get = lambda p: urllib.request.urlopen(f.url + "/repos/o/r" + p)
        self.assertEqual(json.load(get("/issues/71"))["title"], "m3")
        self.assertEqual(f.calls[-1][:2], ("GET", "/repos/o/r/issues/71"))
        r = get("/issues/71/comments?per_page=2")
        self.assertEqual((len(json.load(r)), 'rel="next"' in r.headers["Link"]), (2, True))


if __name__ == "__main__":
    unittest.main()
