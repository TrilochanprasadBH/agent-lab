"""Reference solution for drill 2 — read this after trying your own.

Four moves, in order of payoff:

  1. Weight terms by rarity. A word in two documents tells you far more than a
     word in thirty, and unweighted overlap cannot tell the difference.
  2. Normalise morphology. "evicting", "evicted" and "evict" are one term.
  3. Expand with the alias table — on the *raw query text*, before stemming, or
     multiword aliases like "money back" never fire.
  4. Reward the title and exact phrases. A title is the author's summary of what
     a document is about, and a phrase match is stronger evidence than two loose
     term matches.

This is BM25's shape without its tuning parameters.
"""

from __future__ import annotations

import math
import re

from drills.w02_retrieval.data import ALIASES, documents

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "was", "be", "been", "it", "its", "this", "that", "we", "you", "our",
    "do", "does", "did", "how", "what", "when", "who", "why", "should", "can",
    "at", "by", "from", "after", "before", "into", "if", "not", "no", "so",
}


TITLE_BOOST = 0.85
ALIAS_WEIGHT = 0.6
PHRASE_BOOST = 0.45


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
        stem(token)
        for token in re.findall(r"[a-z0-9]+", text.casefold())
        if token not in STOPWORDS
    ]


def _build_alias_groups() -> list[tuple[re.Pattern[str], set[str]]]:
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


ALIAS_GROUPS = _build_alias_groups()


def expand_query(text: str) -> tuple[set[str], set[str]]:
    """Return (direct terms, alias terms) for a query."""
    direct = set(tokenize(text))
    lowered = text.casefold()
    aliased: set[str] = set()
    for pattern, words in ALIAS_GROUPS:
        if pattern.search(lowered):
            aliased |= words - direct
    return direct, aliased


class Index:
    def __init__(self) -> None:
        self.docs = documents()
        self.tokens: dict[str, list[str]] = {}
        self.titles: dict[str, set[str]] = {}
        self.df: dict[str, int] = {}
        self.n = len(self.docs)

        for doc in self.docs:
            body = tokenize(f"{doc.title} {doc.body}")
            self.tokens[doc.doc_id] = body
            self.titles[doc.doc_id] = set(tokenize(doc.title))
            for term in set(body):
                self.df[term] = self.df.get(term, 0) + 1

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        return math.log((self.n + 1) / (df + 1)) + 1.0

    def search(self, query: str, k: int = 3) -> list[str]:
        direct, aliased = expand_query(query)
        wanted: dict[str, float] = {term: 1.0 for term in direct}
        for term in aliased:
            wanted.setdefault(term, ALIAS_WEIGHT)

        phrase_terms = [t for t in tokenize(query) if self.df.get(t, 0) < self.n * 0.5]
        phrases = [f"{a} {b}" for a, b in zip(phrase_terms, phrase_terms[1:])]

        scored: list[tuple[float, str]] = []
        for doc in self.docs:
            counts: dict[str, int] = {}
            for term in self.tokens[doc.doc_id]:
                counts[term] = counts.get(term, 0) + 1

            score = 0.0
            for term, weight in wanted.items():
                tf = counts.get(term, 0)
                if not tf:
                    continue
                score += self.idf(term) * weight * (1.0 + math.log(tf))
                if term in self.titles[doc.doc_id]:
                    score += TITLE_BOOST * self.idf(term) * weight

            text = f"{doc.title} {doc.body}".casefold()
            for phrase in phrases:
                if phrase in text:
                    score += PHRASE_BOOST * sum(self.idf(t) for t in tokenize(phrase))

            scored.append((score, doc.doc_id))

        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [doc_id for _, doc_id in scored[:k]]


_INDEX: Index | None = None


def retrieve(query, model) -> list[str]:
    global _INDEX
    if _INDEX is None:
        _INDEX = Index()
    return _INDEX.search(query.text)
