"""Drill 19 — Memory under a fixed budget.

Goal
    Answer questions about a long conversation using a memory that fits in 160
    whitespace tokens.

Return
    One answer string per probe, in the order the probes are given.

Run
    python3 run.py --drill w19_memory

Starting point
    Keep the most recent turns that fit and discard the rest. That is the
    default behaviour of every chat window ever shipped, and it is wrong in a
    specific, measurable way: it keeps what was said last and forgets what was
    agreed first.

Full brief
    drills/w19_memory/spec.md
"""

from __future__ import annotations

from .data import BUDGET_TOKENS, count_tokens


def remember(conversation, model) -> list[str]:
    kept: list[str] = []
    used = 0
    for turn in reversed(conversation.turns):
        cost = count_tokens(turn)
        if used + cost > BUDGET_TOKENS:
            break
        kept.append(turn)
        used += cost

    memory = "\n".join(reversed(kept))
    return [model.answer(probe, memory) for probe in conversation.probes]
