"""Reference solution for drill 3 — read this after trying your own.

A budget turns retrieval into a *covering* problem. Ranking tells you which
document is best; covering asks whether the evidence you need is inside the
window. Those are different questions, and the difference is visible: three
relevant documents can miss the answer entirely because all three cover the same
half of the question.

Five moves:

  1. Expand the query with the alias table, on raw text. "throttled" and "rate
     limit" are the same concept and no term counter knows that.
  2. Score with IDF so ubiquitous words stop dominating.
  3. Select by *marginal* gain: after each document, strike its terms from the
     query. The second document is chosen for what the first did not cover.
  4. Prefer gain per token. A short document that answers half the question beats
     a long one that repeats the first document.
  5. Truncate at sentence boundaries, and never spend tokens on a header with no
     evidence behind it.
"""

from __future__ import annotations

import math
import re

from drills.w02_retrieval.data import ALIASES, DOCS
from drills.w03_packing.data import BUDGET_TOKENS, count_tokens

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "was", "be", "it", "its", "this", "that", "we", "you", "our", "do",
    "does", "did", "how", "what", "when", "who", "why", "should", "can", "at",
    "by", "from", "after", "before", "into", "if", "not", "no", "so", "then",
    "them", "they", "us", "allowed", "need", "wants", "know", "keep", "kept",
    "happen", "happens", "even", "just", "again", "still",
}



def stem(term: str) -> str:
    """Crude but consistent: plural and tense collapse, without over-stripping -es."""
    if term.endswith("ies") and len(term) > 5:
        return term[:-3] + "y"
    if re.search(r"(?:s|x|z|ch|sh)es$", term):
        return term[:-2]
    if term.endswith("s") and not term.endswith("ss") and len(term) > 4:
        return term[:-1]
    if term.endswith("ing") and len(term) > 6:
        return term[:-3]
    if term.endswith("ed") and len(term) > 5:
        return term[:-2]
    return term


def tokenize(text: str) -> list[str]:
    return [
        stem(t) for t in re.findall(r"[a-z0-9]+", text.casefold()) if t not in STOPWORDS
    ]


def _alias_groups():
    groups = []
    for key, variants in ALIASES.items():
        words = {stem(key), *[stem(v) for v in variants if " " not in v]}
        for variant in variants:
            words.update(tokenize(variant))
        pattern = re.compile(
            r"\b(?:" + "|".join(re.escape(v.casefold()) for v in (key, *variants)) + r")\b"
        )
        groups.append((pattern, words))
    return groups


ALIAS_GROUPS = _alias_groups()


def expand_query(text: str) -> set[str]:
    terms = set(tokenize(text))
    lowered = text.casefold()
    for pattern, words in ALIAS_GROUPS:
        if pattern.search(lowered):
            terms |= words
    return terms


def _sentences(body: str) -> list[str]:
    return [p for p in re.split(r"(?<=[.!?])\s+", body.strip()) if p]


class Packer:
    def __init__(self) -> None:
        self.docs = DOCS
        self.n = len(DOCS)
        self.tokens = {d.doc_id: tokenize(f"{d.title} {d.body}") for d in DOCS}
        self.df: dict[str, int] = {}
        for doc in DOCS:
            for term in set(self.tokens[doc.doc_id]):
                self.df[term] = self.df.get(term, 0) + 1

    def idf(self, term: str) -> float:
        return math.log((self.n + 1) / (self.df.get(term, 0) + 1)) + 1.0

    def _block(self, doc, remaining: int) -> tuple[str, int, set[str]] | None:
        """Build the largest useful block for this doc inside `remaining` tokens."""
        header_cost = count_tokens(doc.title)
        if header_cost + 2 > remaining:
            return None

        piece = [doc.title]
        cost = header_cost
        for sentence in _sentences(doc.body):
            added = count_tokens(sentence)
            if cost + added + 2 > remaining:
                break
            piece.append(sentence)
            cost += added

        if len(piece) == 1:
            return None

        text = " ".join(piece)
        return text, cost + 2, set(tokenize(text))

    def _relevance(self, doc, wanted: set[str]) -> float:
        counts: dict[str, int] = {}
        for term in self.tokens[doc.doc_id]:
            counts[term] = counts.get(term, 0) + 1
        title = set(tokenize(doc.title))

        total = 0.0
        for term in wanted:
            tf = counts.get(term, 0)
            if not tf:
                continue
            total += self.idf(term) * (1.0 + math.log(tf))
            if term in title:
                total += 0.6 * self.idf(term)
        return total

    def pack(self, question: str) -> str:
        wanted = expand_query(question)
        blocks: list[str] = []
        used = 0
        taken: set[str] = set()

        while used < BUDGET_TOKENS - 2 and len(blocks) < 4:
            best = None
            for doc in self.docs:
                if doc.doc_id in taken:
                    continue
                block = self._block(doc, BUDGET_TOKENS - used)
                if block is None:
                    continue
                text, cost, _terms = block
                relevance = self._relevance(doc, wanted)
                if relevance <= 0:
                    continue
                density = relevance / cost
                if best is None or density > best[0]:
                    best = (density, text, cost, doc.doc_id)

            if best is None:
                break

            _, text, cost, doc_id = best
            blocks.append(text)
            used += cost
            taken.add(doc_id)

        return "\n\n".join(blocks)


_PACKER: Packer | None = None


def pack(question, model) -> str:
    global _PACKER
    if _PACKER is None:
        _PACKER = Packer()
    return _PACKER.pack(question.text)
