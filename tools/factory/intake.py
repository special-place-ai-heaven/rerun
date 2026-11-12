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
