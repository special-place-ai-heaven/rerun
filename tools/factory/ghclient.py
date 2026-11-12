"""Minimal GitHub REST client. Token is read from the environment per call and sent only in the auth header."""
import json, os, re, urllib.request, urllib.error


class GhError(Exception):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


class Client:
    def __init__(self, base, repo, token_env="GH_TOKEN"):
        self.base, self.repo, self.token_env = base.rstrip("/"), repo, token_env

    def __repr__(self):
        return "Client(%s, %s)" % (self.base, self.repo)

    def _open(self, method, url, body=None):
        tok = os.environ.get(self.token_env)
        if not tok:
            raise GhError("no token in environment variable %s" % self.token_env)
        req = urllib.request.Request(url, method=method, headers={"Authorization": "token " + tok,
                                     "Accept": "application/json", "Content-Type": "application/json"},
                                     data=None if body is None else json.dumps(body).encode())
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read() or b"null"), r.headers.get("Link")
        except urllib.error.HTTPError as e:
            raise GhError("%s %s failed: HTTP %d" % (method, url.split("?")[0], e.code), e.code) from None
        except urllib.error.URLError as e:
            raise GhError("%s %s failed: %s" % (method, url.split("?")[0], type(e.reason).__name__)) from None

    def req(self, method, path, body=None):
        return self._open(method, self.base + "/repos/" + self.repo + path, body)[0]

    def get(self, path):
        return self.req("GET", path)

    def pages(self, path, per_page=100):
        url = "%s/repos/%s%s?per_page=%d" % (self.base, self.repo, path, per_page)
        while url:
            data, link = self._open("GET", url)
            yield from data
            m = re.search(r'<([^>]+)>;\s*rel="next"', link or "")
            url = m.group(1) if m else None

    def issue(self, n):
        return self.get("/issues/%d" % n)

    def comments(self, n, per_page=100):
        return list(self.pages("/issues/%d/comments" % n, per_page))

    def commit(self, sha):
        return self.get("/commits/" + sha)

    def statuses(self, sha):
        return self.get("/commits/%s/status" % sha)

    def checks(self, sha):
        return self.get("/commits/%s/check-runs" % sha)["check_runs"]

    def open_pr(self, title, head, base, body=""):
        return self.req("POST", "/pulls", {"title": title, "head": head, "base": base, "body": body})

    def create_issue(self, title, body=""):
        return self.req("POST", "/issues", {"title": title, "body": body})
