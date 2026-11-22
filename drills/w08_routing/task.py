"""Drill 08 - Hitting a quality target under a cost cap.

Goal
    Send each question to a tier that can answer it, and no more than that.

Return
    A dict with keys: answer, tier.
    tier is "cheap" or "strong", and must match what you wrote in the prompt.

Run
    python3 run.py --drill w08_routing

Starting point
    Every question goes to the strong tier. Accuracy is 100% and the cost is twice
    the cap.

Full brief
    drills/w08_routing/spec.md
"""

from __future__ import annotations

PROMPT = """tier: strong
Answer the question in one sentence.
{question}
"""


def answer(query, model) -> dict:
    response = model.complete(PROMPT.format(question=query.text))
    return {"answer": response.text.strip(), "tier": "strong"}
