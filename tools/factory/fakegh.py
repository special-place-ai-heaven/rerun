"""Local fake GitHub REST server for tests: in-memory data, Link-header paging, records calls. Loopback only."""
import json, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs


class Fake:
    def __init__(self, issues=None, comments=None, commits=None, statuses=None, checks=None):
        self.issues, self.comments, self.commits = dict(issues or {}), comments or {}, commits or {}
        self.statuses, self.checks, self.calls, self.next = statuses or {}, checks or {}, [], 72
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def go(self, method):
                u = urlparse(self.path)
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n)) if n else None
                fake.calls.append((method, u.path, body, self.headers.get("Authorization")))
                code, out, link = fake.route(method, u.path.split("/")[4:], parse_qs(u.query))
                data = json.dumps(out).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                if link:
                    self.send_header("Link", link)
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self.go("GET")

            def do_POST(self):
                self.go("POST")

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = "http://127.0.0.1:%d" % self.srv.server_address[1]

    def route(self, m, p, q):
        nf = (404, {"message": "Not Found"}, None)
        if m == "POST" and p in (["issues"], ["pulls"]):
            self.next += 1
            return 201, {"number": self.next - 1}, None
        if m != "GET" or not p:
            return nf
        if p[0] == "issues" and len(p) == 2:
            return (200, self.issues[int(p[1])], None) if int(p[1]) in self.issues else nf
        if p[0] == "issues" and p[2:] == ["comments"]:
            return self.page(self.comments.get(int(p[1]), []), q, "/".join(p))
        if p[0] == "commits" and len(p) == 2:
            return (200, self.commits[p[1]], None) if p[1] in self.commits else nf
        if p[0] == "commits" and p[2:] == ["status"]:
            return 200, self.statuses.get(p[1], []), None
        if p[0] == "commits" and p[2:] == ["check-runs"]:
            return 200, self.checks.get(p[1], {"check_runs": []}), None
        return nf

    def page(self, items, q, path):
        per, pg = int(q.get("per_page", [30])[0]), int(q.get("page", [1])[0])
        link = None
        if pg * per < len(items):
            link = '<%s/repos/o/r/%s?per_page=%d&page=%d>; rel="next"' % (self.url, path, per, pg + 1)
        return 200, items[(pg - 1) * per:pg * per], link

    def start(self):
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def stop(self):
        self.srv.shutdown()
        self.srv.server_close()
