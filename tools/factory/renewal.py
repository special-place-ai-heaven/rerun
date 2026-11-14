"""Whether a sign-in renewal is due, read from list_ai_connections."""


def left(answer):
    """minutesLeft of the default connection's signIn, else None."""
    if not isinstance(answer, dict):
        return None
    connections = answer.get("connections")
    if not isinstance(connections, list):
        return None
    for c in connections:
        if not isinstance(c, dict) or c.get("isDefault") is not True:
            continue
        sign_in = c.get("signIn")
        if not isinstance(sign_in, dict):
            return None
        m = sign_in.get("minutesLeft")
        if isinstance(m, (int, float)) and not isinstance(m, bool):
            return m
        return None
    return None


def due(answer, limit):
    """True when the time left is known and at most limit minutes."""
    m = left(answer)
    return m is not None and m <= limit
