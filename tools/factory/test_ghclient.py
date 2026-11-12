"""ghclient.py tests against the local fake: no network, no real token."""
import contextlib, io, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakegh, ghclient

SECRET = "s3cr3t-token-value"


class Base(unittest.TestCase):
    def setUp(self):
        self.f = fakegh.Fake(issues={71: {"number": 71, "title": "m3"}}, comments={71: [{"id": i} for i in range(5)]})
        self.f.start()
        os.environ["GH_TEST_TOKEN"] = SECRET
        self.c = ghclient.Client(self.f.url, "o/r", token_env="GH_TEST_TOKEN")

    def tearDown(self):
        self.f.stop()
        os.environ.pop("GH_TEST_TOKEN", None)


class Core(Base):
    def test_token_not_leaked(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.c.get("/issues/71")
            with self.assertRaises(ghclient.GhError) as cm:
                self.c.get("/issues/999")
        self.assertEqual(self.f.calls[0][3], "token " + SECRET)  # sent only in the auth header
        self.assertEqual(cm.exception.status, 404)
        for text in (out.getvalue(), err.getvalue(), str(cm.exception), repr(cm.exception), repr(self.c)):
            self.assertNotIn(SECRET, text)
        for method, path, body, _ in self.f.calls:
            self.assertNotIn(SECRET, path + repr(body))

    def test_pagination_follows_link(self):
        self.assertEqual([x["id"] for x in self.c.pages("/issues/71/comments", per_page=2)], [0, 1, 2, 3, 4])
        self.assertEqual(len([c for c in self.f.calls if c[1].endswith("/comments")]), 3)

    def test_missing_token_raises_without_call(self):
        del os.environ["GH_TEST_TOKEN"]
        with self.assertRaises(ghclient.GhError):
            self.c.get("/issues/71")
        self.assertEqual(self.f.calls, [])


if __name__ == "__main__":
    unittest.main()
