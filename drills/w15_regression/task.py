"""Drill 15 — regression gating.

THIS IS THE FILE YOU EDIT.

Target: 90% correct ship / block decisions.

Each pull request carries per-item before/after results, grouped by slice. Return
{"ship": True} or {"ship": False}.

The rule, stated exactly:

    ship   if the aggregate result improves by at least 2 points
           AND no slice regresses by 2 points or more
    block  otherwise

The baseline compares the aggregate only. Twelve of these pull requests improve
their aggregate while making one category worse, and it ships all twelve.
"""

from __future__ import annotations


def gate(pr, model) -> dict:
    before = [b for pairs in pr.slices.values() for b, _ in pairs]
    after = [a for pairs in pr.slices.values() for _, a in pairs]
    return {"ship": (sum(after) / len(after)) > (sum(before) / len(before))}
