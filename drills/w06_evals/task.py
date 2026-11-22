"""Drill 06 - Writing an eval that generalises.

Goal
    Decide whether a support reply is good, in a way that holds on data you have
    not seen.

Return
    True for a good reply, False for a bad one.

Run
    python3 run.py --drill w06_evals

Starting point
    Replies longer than 150 characters are called good. That correlates with the
    label in the training split and not in the test split.

Full brief
    drills/w06_evals/spec.md
"""

from __future__ import annotations


def grade(reply, model) -> bool:
    """Baseline: long replies are good ones. About 70% on train, a coin flip on test."""
    return len(reply.text) > 150
