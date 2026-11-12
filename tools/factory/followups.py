"""Follow-ups by code (rerun#71 C8): a review verdict's follow-up notes become issues, one each, never twice."""
import hashlib, re

NOTE = re.compile(r"^\s*(?:[-*]\s*)?(?:follow-?up|non-?blocking)\s*:\s*(\S.*?)\s*$", re.I)
MARK = re.compile(r"<!-- followup:(\S+) -->")


def notes(verdict, job):
    """[(key, title, body)] for each follow-up / non-blocking line; the key is job + hash of the note text."""
    out = []
    for line in (verdict or "").splitlines():
        m = NOTE.match(line)
        if m:
            text = m.group(1)
            key = "%s-%s" % (job, hashlib.sha1(text.lower().encode()).hexdigest()[:10])
            out.append((key, text[:80], "%s\n\nFrom the review of %s.\n\n<!-- followup:%s -->" % (text, job, key)))
    return out


def known(bodies):
    """Keys already present in issue bodies."""
    return {k for b in bodies for k in MARK.findall(b or "")}

