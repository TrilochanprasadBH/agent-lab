"""Drill 15 - Catching a release that breaks one thing.

Goal
    Decide whether a change may ship, using per-category results and not only the
    average.

Return
    A dict with key: ship (boolean).

Run
    python3 run.py --drill w15_regression

Starting point
    Only the overall averages are compared, so every release that raises the
    average is shipped, including the twelve that break a category.

Full brief
    drills/w15_regression/spec.md
"""

from __future__ import annotations


def gate(pr, model) -> dict:
    before = [b for pairs in pr.slices.values() for b, _ in pairs]
    after = [a for pairs in pr.slices.values() for _, a in pairs]
    return {"ship": (sum(after) / len(after)) > (sum(before) / len(before))}
