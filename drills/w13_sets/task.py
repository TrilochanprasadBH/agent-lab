"""Drill 13 - Designing an eval set.

Goal
    Select 32 items that cover all 16 categories without repeating a source.

Return
    A list of 32 item ids.

Run
    python3 run.py --drill w13_sets

Starting point
    The first 32 items in the pool are taken. The pool is sorted by tag, so this
    covers two categories out of sixteen.

Full brief
    drills/w13_sets/spec.md
"""

from __future__ import annotations

from .data import POOL

SELECT = 32


def select(run, model) -> list[str]:
    return [item.doc_id for item in POOL[:SELECT]]
