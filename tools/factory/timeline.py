"""timeline.py: the status of every job and a Mermaid gantt, read from the ledger without taking its lock.

  python3 timeline.py status [--db PATH]
  python3 timeline.py gantt [--db PATH] [--since ISO]
"""
import argparse, calendar, json, sqlite3, sys, time

END = ("merged", "rejected", "blocked", "failed", "returned")
CRIT = ("blocked", "failed", "rejected", "returned")
LONG_WAIT = 10 * 60
DAY = 24 * 3600
FMT = "%Y-%m-%dT%H:%M:%SZ"


def parse(s):
    return calendar.timegm(time.strptime(s, FMT))


def read_rows(path):
    """Jobs and transitions, read-only: never constructs store.Store, so the writer's lock is not touched."""
    db = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    db.row_factory = sqlite3.Row
    try:
        jobs = [dict(r) for r in db.execute("SELECT * FROM jobs")]
        trs = [dict(r) for r in db.execute("SELECT * FROM transitions ORDER BY id")]
    finally:
        db.close()
    return {"jobs": jobs, "transitions": trs}


def _key(job):
    return (0, int(job), job) if job.isdigit() else (1, 0, job)


def _by_job(rows):
    out = {}
    for t in rows["transitions"]:
        out.setdefault(t["job"], []).append(t)
    return out


def status_lines(rows, now):
    trs = _by_job(rows)
    live, done = [], []
    for j in sorted(rows["jobs"], key=lambda j: _key(j["job"])):
        mine = trs.get(j["job"], [])
        last = mine[-1] if mine else None
        end = parse(last["at"]) if last else parse(j["updated_at"])
        if j["state"] in END:
            if now - end <= DAY:
                done.append("#%s %s: %s" % (j["job"], j["state"], (last or {}).get("reason") or "no reason"))
            continue
        start = end
        for t in reversed(mine):  # the run of transitions that kept this state
            if t["to_state"] != j["state"]:
                break
            start = parse(t["at"])
        data = json.loads(j["data"] or "{}")
        pr = "pr #%s" % j["pr"] if j["pr"] else "pr -"
        w = data.get("waiting") or []
        waits = "waits on %s for %d min" % (", ".join("#%s" % n for n in w), max(0, now - end) // 60) if w else "no waits"
        reason = " | reason: %s" % data["wait_reason"] if data.get("wait_reason") else ""
        live.append("#%s %s for %d min | %s | %s%s" % (j["job"], j["state"], max(0, now - start) // 60, pr, waits, reason))
    return live + done


def _hm(t):
    return time.strftime("%H:%M", time.gmtime(t))


def gantt(rows, now, since):
    out = ["```mermaid", "gantt", "    title Factory jobs, times in UTC", "    dateFormat HH:mm",
           "    axisFormat %H:%M"]
    trs = _by_job(rows)
    for job in sorted(trs, key=_key):
        runs = []  # [state, start]
        for t in trs[job]:
            if not runs or runs[-1][0] != t["to_state"]:
                runs.append([t["to_state"], parse(t["at"])])
        bars = []
        for i, (state, start) in enumerate(runs):
            left = i + 1 < len(runs)
            end = runs[i + 1][1] if left else now
            if end < since:
                continue
            tags = []
            if state in CRIT or (state in ("waiting", "queued") and end - start > LONG_WAIT):
                tags.append("crit")
            if left:
                tags.append("done")
            bars.append("    %s %s :%s" % (job, state, "".join(x + ", " for x in tags) + "%s, %s" % (_hm(max(start, since)), _hm(end))))
        if bars:
            out += ["    section %s" % job] + bars
    out.append("```")
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser(prog="timeline.py")
    p.add_argument("cmd", choices=("status", "gantt"))
    p.add_argument("--db", default="/state/ledger.db")
    p.add_argument("--since")
    a = p.parse_args(argv)
    now = int(time.time())
    rows = read_rows(a.db)
    if a.cmd == "status":
        print("\n".join(status_lines(rows, now)))
    else:
        print(gantt(rows, now, parse(a.since) if a.since else now - DAY))
    return 0


if __name__ == "__main__":
    sys.exit(main())
