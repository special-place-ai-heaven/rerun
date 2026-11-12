"""Plan intake: a plan text with the marker to a validated chunk list."""
import re

import ledger

MARKER = re.compile(r"^PLAN READY\b", re.M)


def parse_plan(text):
    """(chunks, errors): chunks the runner accepts (ledger.shape == []), one error per rejected or duplicate line."""
    text = (text or "").replace("\r\n", "\n")
    if not MARKER.search(text):
        return [], ["no PLAN READY marker"]
    lines = ledger.chunk_lines(text)
    if not lines:
        return [], ["no chunk lines under ## Chunks"]
    chunks, errors, seen = [], [], set()
    for line in lines:
        c = ledger.chunk(line)
        why = ledger.shape(line)
        if why:
            errors.append("%s: %s" % (c["id"], "; ".join(why)))
        elif c["id"] in seen:
            errors.append("%s: duplicate id" % c["id"])
        else:
            seen.add(c["id"])
            chunks.append(c)
    return chunks, errors


def register(st, job, text):
    """Open a job from a plan: (state, errors). The ledger state lists the chunks PENDING; each chunk becomes a ready item
    (builder, paths, deps) and the plain stage `challenge` goes to the stage queue. Nothing is stored when no chunk is valid.
    A dependency is met when its chunk's ready state is 'merged' (see readyq/runner_loop); nothing writes it yet. It belongs
    where a chunk PR merge is seen, not here."""
    chunks, errors = parse_plan(text)
    if not chunks:
        return None, errors
    state = ledger.new(job)
    for c in chunks:
        state["chunks"][c["id"]] = "PENDING"
        deps = [d for d in re.split(r"[\s,]+", c["depends"] or "") if d and d != "-"]
        st.add_ready(job, c["id"], c["paths"], c["builder"] or "", deps)
    st.enqueue(job, "challenge")
    return state, errors
