"""Drill 16 — Serving answers from a semantic cache.

Goal
    Reuse an earlier answer when a new question means the same thing, without
    ever serving an answer to a different question.

Return
    A dict with key "served": one entry per turn, in arrival order. The entry is
    the id of the earlier turn whose answer you are reusing, or None when you
    call the model.

Run
    python3 run.py --drill w16_semantic_cache

Starting point
    The cache is keyed on exact text. Every question is phrased slightly
    differently, so it never hits, and every turn pays for a model call.

Full brief
    drills/w16_semantic_cache/spec.md
"""

from __future__ import annotations


def serve(day, model) -> dict:
    seen: dict[str, str] = {}
    served: list[str | None] = []

    for turn in day.turns:
        key = turn.text.strip().lower()
        if key in seen:
            served.append(seen[key])
        else:
            model.complete(turn.text)
            seen[key] = turn.id
            served.append(None)

    return {"served": served}
