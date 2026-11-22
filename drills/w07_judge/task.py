"""Drill 07 - Getting a reliable answer out of a noisy judge.

Goal
    Combine several noisy judgements into one reliable preference.

Return
    "A", "B", or "tie".

Run
    python3 run.py --drill w07_judge

Starting point
    The judge is called once, in one order, and its verdict is returned. Position
    bias is not corrected and noise is not outvoted.

Full brief
    drills/w07_judge/spec.md
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
