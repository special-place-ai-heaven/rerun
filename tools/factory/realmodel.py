#!/usr/bin/env python3
"""A real model for the development engine through a Claude subscription, and a one-run proof (rerun#71).
Runs inside the runner container, which already holds the dev engine's address and key:
    python3 /app/realmodel.py check            is the connection there; which connection is the default
    python3 /app/realmodel.py connect          reads the subscription token from standard input, creates the connection
    python3 /app/realmodel.py probe [model]    one short run on the real model: status, model and token counts
    python3 /app/realmodel.py remove           deletes the connection
The token (from `claude setup-token`) is read from standard input only, sent once to the dev engine in a request
body, and kept nowhere else: no file, no command line, no output. Errors name the step and the HTTP status only."""
import os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # own dir first, as the other factory tools do
import engine as E

NAME, PROBE, MODEL = "claude-plan", "real-model-probe", "claude-haiku-5-5"
TOKEN_KEY = "CLAUDE_CODE_OAUTH_TOKEN"
TOKEN_OK = re.compile(r"[A-Za-z0-9_.~+/=-]{20,}")
LONG = re.compile(r"[A-Za-z0-9_.~+/=-]{30,}")  # anything shaped like a credential is cut from an error text
PROMPT = "Reply with the single word READY and nothing else. Use no tools."
WAIT_S, STEP_S = 180, 3


def find(eng):
    """(the subscription connection or None, the id of the default connection or None)."""
    listing = eng._call("GET", "/connections")
    conn = next((c for c in listing.get("connections") or [] if c.get("name") == NAME and c.get("provider") == "claude"), None)
    return conn, (listing.get("default") or {}).get("connectionId")


def check(eng):
    conn, default = find(eng)
    return ["connection=%s default-is-real-model=%s" % ("present" if conn else "absent", "yes" if conn and default == conn["id"] else "no")]


def connect(eng, token):
    token = (token or "").strip()
    if not TOKEN_OK.fullmatch(token):
        raise ValueError("the token is empty or does not look like a token; nothing was sent")
    conn, _ = find(eng)
    if conn:
        eng._call("PATCH", "/connections/%s/keys" % E._q(conn["id"]), payload={"set": {TOKEN_KEY: token}})
        return ["connection=updated"]
    eng._call("POST", "/connections", payload={"name": NAME, "provider": "claude", "keys": {TOKEN_KEY: token}})
    return ["connection=created"] + check(eng)


def probe(eng, model=MODEL, sleep=time.sleep):
    """One coworker on the real model, one trigger, one run. The coworker is deleted again whatever happens."""
    conn, _ = find(eng)
    if not conn:
        raise RuntimeError("no %s connection yet: run connect first" % NAME)
    agent = eng._call("POST", "/agents", payload={"config": {
        "name": PROBE, "description": "One-run proof that the real model answers (dev engine)",
        "connectionId": conn["id"], "provider": "claude", "model": model}})
    try:
        trig = eng.create_trigger(agent["id"], "probe", PROMPT)
        run_id, _ = eng.fire_trigger(agent["id"], trig["slug"], trig["token"], {})
        row, waited = {"status": "running"}, 0
        while row.get("status") == "running" and waited < WAIT_S:
            sleep(STEP_S)
            waited += STEP_S
            row = eng.get_run(agent["id"], run_id) or {"status": "missing"}
    finally:
        eng._call("DELETE", "/agents/%s" % E._q(agent["id"]))
    err = LONG.sub("<cut>", row.get("error") or "")[:160]
    return ["run=%s status=%s provider=%s model=%s input-tokens=%s output-tokens=%s%s" % (
        run_id, row.get("status"), row.get("provider"), row.get("model"), row.get("inputTokens"), row.get("outputTokens"),
        " error=%s" % err if err else "")]


def remove(eng):
    conn, _ = find(eng)
    if not conn:
        return ["connection=absent"]
    eng._call("DELETE", "/connections/%s" % E._q(conn["id"]))
    return ["connection=removed"]


def main(argv=None, stdin=sys.stdin):
    a = list(sys.argv[1:] if argv is None else argv) or ["check"]
    try:
        eng = E.Engine()
        if a[0] == "check":
            out = check(eng)
        elif a[0] == "connect":
            out = connect(eng, stdin.readline())
        elif a[0] == "probe":
            out = probe(eng, *a[1:2])
        elif a[0] == "remove":
            out = remove(eng)
        else:
            print("usage: realmodel.py check|connect|probe [model]|remove", file=sys.stderr)
            return 2
    except (E.EngineError, ValueError, RuntimeError, KeyError) as e:
        print("realmodel %s failed: %s" % (a[0], "unexpected engine answer" if isinstance(e, KeyError) else e), file=sys.stderr)
        return 1
    for line in out:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
