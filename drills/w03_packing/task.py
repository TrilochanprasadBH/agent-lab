"""Drill 03 - Fitting evidence into a budget.

Goal
    Assemble the documents a question needs into a single string of at most 120
    words.

Return
    One string, containing the evidence for each required question.

Run
    python3 run.py --drill w03_packing

Starting point
    Documents are appended in corpus order until the budget is full. The question
    is ignored entirely.

Full brief
    drills/w03_packing/spec.md
"""

from __future__ import annotations

import re

from .data import BUDGET_TOKENS, DOC_INDEX, count_tokens
from drills.w02_retrieval.data import DOCS

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "was", "be", "it", "its", "this", "that", "we", "you", "our", "do",
    "does", "did", "how", "what", "when", "who", "why", "should", "can", "at",
    "by", "from", "after", "before", "into", "if", "not", "no", "so", "then",
}


def tokenize(text: str) -> list[str]:
    return [
        t for t in re.findall(r"[a-z0-9]+", text.casefold()) if t not in STOPWORDS
    ]


def pack(question, model) -> str:
    """Naive packing: take documents in corpus order until the budget runs out."""
    chunks: list[str] = []
    used = 0
    for doc in DOCS:
        block = f"{doc.title}\n{doc.body}"
        cost = count_tokens(block)
        if used + cost > BUDGET_TOKENS:
            break
        chunks.append(block)
        used += cost
    return "\n\n".join(chunks)
