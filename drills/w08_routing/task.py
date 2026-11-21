"""Drill 8 — routing by cost.

THIS IS THE FILE YOU EDIT.

Target: 92% correct answers, under $0.030 total.

Two tiers, and you pick per query by writing "tier: cheap" or "tier: strong" into
the prompt:

    cheap    $0.0002   right on lookups, wrong on reasoning
    strong   $0.0015   right on everything

Return {"answer": ..., "tier": ...}.

The baseline sends everything to the strong tier. It is 100% accurate and
$0.060 over budget.
"""

from __future__ import annotations

PROMPT = """tier: strong
Answer the question in one sentence.
{question}
"""


def answer(query, model) -> dict:
    response = model.complete(PROMPT.format(question=query.text))
    return {"answer": response.text.strip(), "tier": "strong"}
