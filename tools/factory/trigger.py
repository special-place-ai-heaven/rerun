#!/usr/bin/env python3
"""Trigger client of the factory runner (rerun#53 chunk 1). Fires a coworker's webhook trigger once and reads the run
from that coworker's system.db, read only. Commands: probe --stage STAGE | check-triggers.
A trigger URL carries a secret token: no code path here prints, logs or raises the URL or the token."""
import json, os, pathlib, sqlite3, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = "/data/agents"
ENV = "/data/factory/runner.env"
CONFIG = os.path.join(HERE, "runner.json")
TRIGGERS = os.path.join(HERE, "triggers")
PROBE_WAIT_S, PROBE_POLL_S, PROBE_MAX_INPUT = 600, 15, 300000
RUN_COLS = ("id", "agent_id", "session_id", "status", "step_count", "usage_json", "started_at", "finished_at", "error",
            "input_tokens", "output_tokens", "cached_input_tokens", "trigger_source", "trigger_slug")


class TriggerError(Exception):
    """Its message never holds the trigger URL or token."""


def load_config(path=None):
    with open(path or CONFIG, encoding="utf-8") as f:
        return json.load(f)


def trigger_url(stage, coworker, path=None):
    """FACTORY_TRIGGER_<STAGE>_<COWORKER> from the env file (KEY=VALUE lines)."""
    key = "FACTORY_TRIGGER_%s_%s" % (stage.upper(), coworker.upper())
    try:
        with open(path or ENV, encoding="utf-8") as f:
            for line in f:
                k, sep, v = line.strip().partition("=")
                if sep and k.strip() == key and v.strip():
                    return v.strip().strip("\"'")
    except OSError as e:
        raise TriggerError("cannot read the env file (%s)" % type(e).__name__) from None
    raise TriggerError("%s is not set in the env file" % key)


def fire(url, payload, urlopen=urllib.request.urlopen):
    """POST the payload once as compact JSON; (runId, sessionId) from the 202 answer. Never retried: a timeout may
    still have started a run. Errors carry the HTTP status or the error class only, never the URL or the answer."""
    data = json.dumps(payload, separators=(",", ":")).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=30) as r:
            code, raw = r.status, r.read()
    except urllib.error.HTTPError as e:
        raise TriggerError("trigger answered HTTP %d" % e.code) from None
    except Exception as e:
        raise TriggerError("trigger call failed (%s)" % type(e).__name__) from None
    try:
        body = json.loads(raw.decode() or "{}")
    except ValueError:
        body = None
    if code != 202 or not isinstance(body, dict) or not body.get("runId"):
        raise TriggerError("trigger answered HTTP %d without a run id" % code)
    return body["runId"], body.get("sessionId")


def db_path(agent):
    return os.path.join(AGENTS, agent, "data", "system.db")


def read_run(agent, run_id, path=None):
    """The runs row of run_id with RUN_COLS picked by name (a missing column reads as None), or None for no row.
    Read only: mode=ro and query_only, so the file is never created or written. Raises sqlite3.Error if it cannot open."""
    con = sqlite3.connect(pathlib.Path(path or db_path(agent)).as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        con.execute("PRAGMA query_only=1")
        cur = con.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cur.fetchone()
        names = [d[0] for d in cur.description]
    finally:
        con.close()
    if row is None:
        return None
    got = dict(zip(names, row))
    return {k: got.get(k) for k in RUN_COLS}


def input_tokens(row):
    """Column input_tokens, else usage_json inputTokens, else None."""
    if row.get("input_tokens") is not None:
        return row["input_tokens"]
    try:
        return json.loads(row.get("usage_json") or "null")["inputTokens"]
    except (TypeError, KeyError, ValueError):
        return None


def split_front(text):
    """(front matter lines, body) of a trigger file; the body stripped as the engine's loader does. None if never closed."""
    lines = text.replace("\r\n", "\n").split("\n")
    if lines[0].strip() != "---":
        return [], text.replace("\r\n", "\n").strip()
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return None, ""
    return lines[1:end], "\n".join(lines[end + 1:]).strip()


def model_of(front):
    v = next((l.split(":", 1)[1].strip() for l in front if l.startswith("model:")), "")
    v = v.strip("\"'")
    return None if v in ("", "null", "~") else v


def cmd_check_triggers(a):
    """<slug> OK|DRIFT per runner.json entry: live body and model against triggers/<stage>.md and runner.json.
    Nothing else is printed (the front matter holds the token), not even why."""
    entries = load_config()["triggers"]
    slugs = [e["slug"] for e in entries]
    bad = 0
    for e in entries:
        try:
            with open(os.path.join(AGENTS, e["agent"], "triggers", e["slug"] + ".md"), encoding="utf-8") as f:
                front, body = split_front(f.read())
            with open(os.path.join(TRIGGERS, e["stage"] + ".md"), encoding="utf-8") as f:
                want = f.read().replace("\r\n", "\n").strip()
            ok = front is not None and body == want and model_of(front) == e.get("model")
        except Exception:
            ok = False
        bad += 0 if ok else 1
        label = e["slug"] if slugs.count(e["slug"]) == 1 else "%s %s" % (e["slug"], e["coworker"])  # build/review: one slug, three coworkers
        print("%s %s" % (label, "OK" if ok else "DRIFT"))
    return 1 if bad else 0


def cmd_probe(a):
    stage = a[a.index("--stage") + 1] if "--stage" in a[:-1] else ""
    entries = [e for e in load_config()["triggers"] if e["stage"] == stage]
    if len(entries) != 1:
        print("usage: probe --stage STAGE (a stage with exactly one trigger in runner.json)")
        return 2
    e = entries[0]
    try:
        run_id, sid = fire(trigger_url(stage, e["coworker"]), {"v": 1, "stage": "probe"})
        end = time.time() + PROBE_WAIT_S
        while True:
            row = read_run(e["agent"], run_id) or {}
            if row.get("status") not in (None, "running") or time.time() >= end:
                break
            time.sleep(PROBE_POLL_S)
    except (TriggerError, sqlite3.Error) as x:
        print("PROBE FAIL: %s" % x)
        return 1
    n, st = input_tokens(row), row.get("status")
    ok = st == "done" and n is not None and n < PROBE_MAX_INPUT
    print("%s %s %s input=%s%s" % ("PROBE OK" if ok else "PROBE FAIL", run_id, sid, "?" if n is None else n, "" if ok else " status=%s" % st))
    return 0 if ok else 1


CMDS = {"probe": cmd_probe, "check-triggers": cmd_check_triggers}


def main(argv):
    if not argv or argv[0] not in CMDS:
        print("commands: " + ", ".join(CMDS))
        return 2
    try:
        return CMDS[argv[0]](argv[1:])
    except Exception as e:  # anything unforeseen: the class name only, a message could quote the URL
        print("FAILED (%s)" % type(e).__name__)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
