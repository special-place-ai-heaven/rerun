"""Whether a sign-in renewal is due, read from list_ai_connections."""


def left(answer):
    """Smallest minutesLeft among connections with a signIn, else None."""
    if not isinstance(answer, dict):
        return None
    connections = answer.get("connections")
    if not isinstance(connections, list):
        return None
    values = []
    for c in connections:
        sign_in = c.get("signIn") if isinstance(c, dict) else None
        if not isinstance(sign_in, dict):
            continue
        m = sign_in.get("minutesLeft")
        if isinstance(m, (int, float)) and not isinstance(m, bool):
            values.append(m)
    return min(values) if values else None


def due(answer, limit):
    """True when the time left is known and at most limit minutes."""
    m = left(answer)
    return m is not None and m <= limit
