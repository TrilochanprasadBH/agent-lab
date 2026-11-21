"""Easy questions, hard questions, and two models with very different prices.

The cheap model handles lookups correctly and fails at anything requiring
reasoning. The strong model is right about everything and costs 7.5x more.

Calling the strong model for everything busts the budget. Calling the cheap model
for everything passes the budget and fails a third of the questions. The only way
through is to look at the question before you decide.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

EASY_TEMPLATES = [
    ("what is the status of order {ref}", "order {ref} shipped on the 14th"),
    ("how many orders does customer {ref} have", "customer {ref} has 3 orders"),
    ("list the open tickets for {ref}", "{ref} has 2 open tickets"),
    ("what plan is {ref} on", "{ref} is on the pro plan"),
    ("what is the total on invoice {ref}", "invoice {ref} totals 120.50"),
]

HARD_TEMPLATES = [
    ("why did the nightly job fail for {ref}", "the job for {ref} failed because the lockfile changed and the cache missed"),
    ("debug why {ref} is slow at peak", "{ref} is slow because the connection pool is undersized for peak load"),
    ("compare the two refund paths for {ref}", "for {ref}, the card path is faster but irreversible; the wallet path is reversible"),
    ("design a retry policy for {ref}", "for {ref}, retry with exponential backoff and a 24 hour cap"),
    ("explain the root cause of the {ref} incident", "the {ref} incident was caused by a DNS TTL that was never lowered before cutover"),
    ("what tradeoff should we make for {ref}", "for {ref}, accept slightly higher latency to avoid double writes"),
]


@dataclass(frozen=True)
class Query:
    doc_id: str
    text: str
    answer: str
    difficulty: str
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.text)


def build() -> list[Query]:
    refs = ["c100", "c200", "8712", "8713", "9000", "4410", "2277", "6601"]
    queries: list[Query] = []
    index = 0

    for template, answer in EASY_TEMPLATES * 5:
        ref = refs[index % len(refs)]
        queries.append(
            Query(
                doc_id=f"r{index + 1:02d}",
                text=template.format(ref=ref),
                answer=answer.format(ref=ref),
                difficulty="easy",
            )
        )
        index += 1

    for template, answer in HARD_TEMPLATES * 3:
        if index >= 40:
            break
        ref = refs[index % len(refs)]
        queries.append(
            Query(
                doc_id=f"r{index + 1:02d}",
                text=template.format(ref=ref),
                answer=answer.format(ref=ref),
                difficulty="hard",
            )
        )
        index += 1

    return queries


QUERIES = build()

CHEAP_COST = 0.0002
STRONG_COST = 0.0015


def _unit(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:13], 16) / float(16**13)


class TieredModel:
    """One model, two tiers, two prices. The tier is chosen by the caller."""

    name = "tiered"

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self._cost = 0.0
        self._latencies: list[float] = []

    def reset(self) -> None:
        self.calls.clear()
        self._cost = 0.0
        self._latencies.clear()

    @property
    def cost_usd(self) -> float:
        return self._cost

    @property
    def latencies(self) -> list[float]:
        return list(self._latencies)

    @property
    def n_calls(self) -> int:
        return len(self.calls)

    def complete(self, prompt: str, system: str | None = None):
        from agentlab.model import Response

        strong = "tier: strong" in prompt
        tier = "strong" if strong else "cheap"

        query = next((q for q in QUERIES if q.text in prompt), None)
        if query is None:
            text = "I don't know."
            cost = CHEAP_COST
        elif strong:
            text = query.answer
            cost = STRONG_COST
        elif query.difficulty == "easy":
            text = query.answer
            cost = CHEAP_COST
        else:
            text = "It is probably a caching issue."
            cost = CHEAP_COST

        latency = 80.0 + (900.0 if strong else 120.0) * _unit(prompt, "lat")
        self._cost += cost
        self._latencies.append(latency)
        self.calls.append({"tier": tier, "cost_usd": cost, "latency_ms": latency})
        return Response(
            text=text,
            tokens_in=max(1, len(prompt) // 4),
            tokens_out=max(1, len(text) // 4),
            latency_ms=latency,
            cost_usd=cost,
        )


def corpus() -> list[Query]:
    return list(QUERIES)
