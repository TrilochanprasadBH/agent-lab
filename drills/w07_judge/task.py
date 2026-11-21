"""Drill 7 — judging output you cannot read by hand.

THIS IS THE FILE YOU EDIT.

Target: 85% agreement with the human preference labels, under a $0.015 cap.

The judge is right about 86% of the time on a single call, and it has a position
bias: when it is unsure it prefers whichever response came first.

One call per pair is not enough. Two calls, in both orders, is usually enough —
and it is the classic fix for this exact defect. More samples reduce noise but
cost money, and the cap is real.

Return "A", "B" or "tie".
"""

from __future__ import annotations

PROMPT = """Which response is better for the question? Answer with one line:
Winner: A, Winner: B, or Winner: tie.

Question: {question}

RESPONSE A:
{a}

RESPONSE B:
{b}
"""


def judge(pair, model) -> str:
    response = model.complete(
        PROMPT.format(question=pair.question, a=pair.a, b=pair.b)
    )
    return _parse(response.text)


def _parse(text: str) -> str:
    lowered = text.casefold()
    if "tie" in lowered:
        return "tie"
    if "winner: a" in lowered:
        return "A"
    if "winner: b" in lowered:
        return "B"
    return "tie"
