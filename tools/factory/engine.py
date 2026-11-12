#!/usr/bin/env python3
"""HTTP client of the development engine (rerun#60 chunk C3a). Reads run rows and cancels runs over the engine's routes:
GET /agents/:id/runs, GET .../runs/:rid, GET .../runs/:rid/steps, POST .../runs/:rid/cancel.
The key is read from one env var and sent only as a Bearer header to the base URL. No code path prints, logs or raises
the key, and an error carries the HTTP status or the error class only, never the answer body."""
import json, os, urllib.error, urllib.parse, urllib.request

KEY_ENV, URL_ENV = "RERUN_DEV_ENGINE_KEY", "RERUN_DEV_ENGINE_URL"
TIMEOUT_S = 30


class EngineError(Exception):
    """Its message never holds the key or an answer body."""


def _q(s):
    return urllib.parse.quote(s, safe="")


class Engine:
    def __init__(self, base_url=None, key=None, urlopen=urllib.request.urlopen, timeout=TIMEOUT_S):
        self.base = (base_url or os.environ.get(URL_ENV) or "").rstrip("/")
        self._key = key if key is not None else os.environ.get(KEY_ENV, "")
        if not self.base:
            raise EngineError("%s is not set" % URL_ENV)
        if not self._key:
            raise EngineError("%s is not set" % KEY_ENV)
        self._urlopen, self._timeout = urlopen, timeout

    def __repr__(self):
        return "Engine(%s)" % self.base

    def _call(self, method, path, query=None):
        url = self.base + path + ("?" + urllib.parse.urlencode(query) if query else "")
        headers = {"Authorization": "Bearer " + self._key, "Accept": "application/json"}
        data = b"{}" if method == "POST" else None
        if data:
            headers["Content-Type"] = "application/json"
        try:
            req = urllib.request.Request(url, data=data, method=method, headers=headers)
            with self._urlopen(req, timeout=self._timeout) as r:
                code, raw = r.status, r.read()
        except urllib.error.HTTPError as e:
            raise EngineError("engine answered HTTP %d for %s %s" % (e.code, method, path)) from None
        except Exception as e:
            raise EngineError("engine call failed (%s) for %s %s" % (type(e).__name__, method, path)) from None
        try:
            body = json.loads(raw.decode() or "{}")
        except ValueError:
            raise EngineError("engine answered HTTP %d with a body that is not JSON" % code) from None
        if not isinstance(body, dict):
            raise EngineError("engine answered HTTP %d with an unexpected body" % code)
        return body

    @staticmethod
    def _run_path(agent_id, run_id):
        return "/agents/%s/runs/%s" % (_q(agent_id), _q(run_id))

    def list_runs(self, agent_id, status=None, limit=50):
        query = {"limit": int(limit)}
        if status:
            query["status"] = status
        runs = self._call("GET", "/agents/%s/runs" % _q(agent_id), query).get("runs")
        if not isinstance(runs, list):
            raise EngineError("engine answered without a runs list")
        return runs

    def get_run(self, agent_id, run_id):
        """The run row, or None when the engine does not know it (404)."""
        try:
            return self._call("GET", self._run_path(agent_id, run_id))
        except EngineError as e:
            if "HTTP 404" in str(e):
                return None
            raise

    def run_steps(self, agent_id, run_id):
        steps = self._call("GET", self._run_path(agent_id, run_id) + "/steps").get("steps")
        if not isinstance(steps, list):
            raise EngineError("engine answered without a steps list")
        return steps

    def cancel(self, agent_id, run_id):
        """Cancel one run; True when the engine answered ok. Not retried by this client."""
        return self._call("POST", self._run_path(agent_id, run_id) + "/cancel").get("ok") is True
