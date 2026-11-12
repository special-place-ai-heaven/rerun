"""measures.py: queue measures, pure. ready: rows {job, chunk, added_at}; fires: rows {job, chunk, stage, intent_at, ended_at};
now: ISO time. Returns {depth: chunks still waiting, wait_s: [seconds each chunk waited], stalled_s: seconds with a chunk
waiting while a builder slot was free}."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import limits as L


def queue_measures(ready, fires, now, cfg=None):
    end = L.ts(now)
    builds = [f for f in fires if f["stage"] == "build"]
    start = {}
    for f in builds:
        k, t = (f["job"], f["chunk"]), L.ts(f["intent_at"])
        start[k] = min(t, start.get(k, t))
    spans = [(L.ts(r["added_at"]), start.get((r["job"], r["chunk"]), end)) for r in ready]
    busy = [(L.ts(f["intent_at"]), L.ts(f["ended_at"]) if f.get("ended_at") else end) for f in builds]
    edges = sorted({t for s in spans + busy for t in s})
    stalled = 0.0
    for a, b in zip(edges, edges[1:]):
        waiting = any(s <= a and b <= e for s, e in spans)
        if waiting and sum(1 for s, e in busy if s <= a and b <= e) < L.capacity(cfg):
            stalled += b - a
    return {"depth": sum(1 for r in ready if (r["job"], r["chunk"]) not in start),
            "wait_s": [e - s for s, e in spans], "stalled_s": stalled}
