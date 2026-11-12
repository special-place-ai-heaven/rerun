"""Wake claims: one start per (event, coworker, head). Runner-made events are named review-ready:<pr>."""


def review_event(pr):
    return "review-ready:%s" % pr


def claim_wake(store, event, coworker, head):
    """True when this wake is new and the caller may start the run; False when already claimed."""
    return store.add_wake(event, coworker, head)
