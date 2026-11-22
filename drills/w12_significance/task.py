"""Drill 12 - Deciding whether a change is real.

Goal
    Decide, from two eval runs, whether a change should ship.

Return
    A dict with key: ship (boolean).

Run
    python3 run.py --drill w12_significance

Starting point
    The two averages are compared and B ships when it is higher. Noise and
    different question sets are both treated as improvement.

Full brief
    drills/w12_significance/spec.md
"""

from __future__ import annotations


def decide(run, model) -> dict:
    a = sum(run.a.values()) / len(run.a)
    b = sum(run.b.values()) / len(run.b)
    return {"ship": b > a}
