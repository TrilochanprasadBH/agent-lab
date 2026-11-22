"""Drill 12 — is the difference real?

THIS IS THE FILE YOU EDIT.

Target: 90% correct ship / no-ship decisions across 35 eval-run comparisons.

Each item is one run pair:

    run.a   {item_id: passed}   the current system
    run.b   {item_id: passed}   the candidate

Return {"ship": True} or {"ship": False}.

Three things to notice before you write anything:

  1. Some pairs share item ids and some do not. What does that mean for comparing
     their averages?
  2. Two runs on the same items are *paired observations*, not two samples.
  3. A difference of 2 points on 48 items is not automatically a difference.

The baseline compares the two averages and ships if B is higher. It is right
about half the time on runs that changed nothing.
"""

from __future__ import annotations


def decide(run, model) -> dict:
    a = sum(run.a.values()) / len(run.a)
    b = sum(run.b.values()) / len(run.b)
    return {"ship": b > a}
