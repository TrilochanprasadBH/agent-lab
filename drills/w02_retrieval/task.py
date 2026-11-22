"""Drill 02 - Finding the right document.

Goal
    Return the documents most likely to answer a question, best first.

Return
    A list of document ids, length 3, ordered by relevance.

Run
    python3 run.py --drill w02_retrieval

Starting point
    Documents are ranked by how many question words they contain. Rare words and
    common words count the same, and word forms do not match.

Full brief
    drills/w02_retrieval/spec.md
"""

from __future__ import annotations

import re

from .data import documents

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "was", "be", "been", "it", "its", "this", "that", "we", "you", "our",
    "do", "does", "did", "how", "what", "when", "who", "why", "should", "can",
    "at", "by", "from", "after", "before", "into", "if", "not", "no", "so",
}


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text.casefold())
        if token not in STOPWORDS
    ]


def retrieve(query, model) -> list[str]:
    query_terms = set(tokenize(query.text))

    ranked: list[tuple[int, str]] = []
    for doc in documents():
        doc_terms = set(tokenize(f"{doc.title} {doc.body}"))
        overlap = len(query_terms & doc_terms)
        ranked.append((overlap, doc.doc_id))

    ranked.sort(key=lambda pair: (-pair[0], pair[1]))
    return [doc_id for _, doc_id in ranked[:3]]
