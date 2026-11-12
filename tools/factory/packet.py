"""Retry packet: the first packet plus the tail of the failure, inside the packet cap."""

PACKET_CAP = 4096  # bytes; wave 2's C3a reads the lane value from settings
HEAD = "\n## Failure tail (last output of the previous attempt)\n"


def _fit(text, room):
    return text.encode()[:max(room, 0)].decode("utf-8", "ignore")


def retry_packet(base, failure, cap=PACKET_CAP):
    """base + the END of failure, never more than cap bytes; the tail is cut at a line start when it can be."""
    head = base + HEAD
    room = cap - len(head.encode())
    if room <= 0:
        return _fit(base, cap)
    raw = (failure or "").rstrip().encode()
    if len(raw) > room:
        raw = raw[-room:]
        nl = raw.find(b"\n")
        raw = raw[nl + 1:] if 0 <= nl < len(raw) - 1 else raw
    return head + raw.decode("utf-8", "ignore")
