"""Wake claims: one start per (event, coworker, head). Runner-made events are named review-ready:<pr>."""


def review_event(pr):
    return "review-ready:%s" % pr


def claim_wake(store, event, coworker, head):
    """True when this wake is new and the caller may start the run; False when already claimed."""
    return store.add_wake(event, coworker, head)


ENDED_BAD = ("failed", "cancelled", "missing")


def end_wake(store, event, coworker, head, status):
    """Release the claim when the run ended failed, cancelled or missing, so the same head can fire again.
    True when a claim was released."""
    return store.release_wake(event, coworker, head) if status in ENDED_BAD else False
