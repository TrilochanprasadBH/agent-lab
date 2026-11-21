"""Drill 6 — writing an eval that generalises.

THIS IS THE FILE YOU EDIT.

Target: 90% agreement with the human labels on the held-out test set.

Study the train set:

    python3 -c "from drills.w06_evals.data import train_examples; \
        [print(label, '|', r.text) for r, label in train_examples()[:6]]"

Then write a grader that encodes *why* a reply is good, not what the good replies
in that split happen to look like.

Scoring uses the test split, whose labels you cannot see from here. A grader that
keys on surface features of the train split will score well below the target, and
that is the point.
"""

from __future__ import annotations


def grade(reply, model) -> bool:
    """Baseline: long replies are good ones. About 70% on train, a coin flip on test."""
    return len(reply.text) > 150
