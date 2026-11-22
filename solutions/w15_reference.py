"""Reference solution for drill 15 — read this after trying your own.

One idea: **an aggregate is a summary, and summaries hide distributions.**

A gate that only looks at the average will ship a release that improves refunds by
30% and breaks international by 15%, because 30 > 15 in the one number it sees.
The customers who are international do not experience the average.

The implementation is four lines: compute the aggregate delta, compute each slice
delta, require the first to clear a floor and the second to clear a different
floor. The judgment is in choosing those floors — and in deciding, per slice,
which regression is even acceptable.

Two rules worth carrying to any real eval gate:

  - **Never gate on a single number.** Gate on the aggregate *and* the worst
    slice. The worst slice is where the incident comes from.
  - **Asymmetric costs.** A false ship reaches users; a false block costs an hour
    of an engineer's time. Set thresholds so the asymmetry is visible in the code,
    not just in the review discussion.
"""

from __future__ import annotations

AGGREGATE_FLOOR = 0.02
SLICE_FLOOR = -0.02


def gate(pr, model) -> dict:
    before = [b for pairs in pr.slices.values() for b, _ in pairs]
    after = [a for pairs in pr.slices.values() for _, a in pairs]

    aggregate_delta = (sum(after) / len(after)) - (sum(before) / len(before))

    slice_deltas = {
        name: (sum(a for _, a in pairs) - sum(b for b, _ in pairs)) / len(pairs)
        for name, pairs in pr.slices.items()
    }
    worst_slice = min(slice_deltas.items(), key=lambda kv: kv[1])

    ship = aggregate_delta >= AGGREGATE_FLOOR and worst_slice[1] >= SLICE_FLOOR
    return {
        "ship": ship,
        "aggregate_delta": round(aggregate_delta, 4),
        "worst_slice": (worst_slice[0], round(worst_slice[1], 4)),
    }
