"""Pairwise preferences, and a judge that is right most of the time.

Two defects are injected into the judge on purpose:

  - **noise**: some fraction of calls simply pick the worse answer;
  - **position bias**: when uncertain, the judge leans toward whichever response
    appears first in the prompt.

Only one of those is fixable by asking the same question again. The other is
fixed by asking it twice, in both orders, and comparing.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

QUESTIONS = [
    "summarise the refund policy in two sentences",
    "explain why the build is slow",
    "draft a reply to an angry customer",
    "what does this error mean",
    "rewrite this paragraph more clearly",
    "list the steps to rotate a credential",
]

GOOD = [
    "Refunds are available within 30 days of purchase. Partial refunds cannot exceed the captured amount.",
    "The build is slow because the dependency cache misses on every lockfile change, which forces a full resolve.",
    "I understand the frustration, and I want to fix this. I have reversed the duplicate charge and it will land within three business days.",
    "That error means the request exceeded the token budget, so the context was truncated before the model saw it.",
    "The paragraph says the same thing three times; it needs one claim, one piece of evidence, and a conclusion.",
    "Rotate the credential in the vault, redeploy so consumers read the new version, then revoke the old secret.",
]

BAD = [
    "Refunds are handled case by case depending on the situation and the team's judgement at the time.",
    "The build is slow for various reasons related to how the system works internally.",
    "We are sorry for the inconvenience and will look into this as soon as possible.",
    "That error is a known issue and has been reported to the relevant team.",
    "The paragraph could possibly be improved in a number of different ways depending on what you want.",
    "You should rotate the credential at some point and make sure everything still works afterwards.",
]


@dataclass(frozen=True)
class Pair:
    doc_id: str
    question: str
    a: str
    b: str
    truth: str  # "A", "B" or "tie"
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.doc_id)


def build() -> tuple[list[Pair], dict[str, float]]:
    rng = random.Random(2027)
    pairs: list[Pair] = []
    quality: dict[str, float] = {}

    for index in range(36):
        question = QUESTIONS[index % len(QUESTIONS)]
        good = GOOD[index % len(GOOD)]
        bad = BAD[index % len(BAD)]

        kind = index % 6
        if kind == 5:  # tie: two different good answers
            other = GOOD[(index + 1) % len(GOOD)]
            a, b, truth = good, other, "tie"
            quality[a] = 1.0
            quality[b] = 1.0
        elif index % 2 == 0:
            a, b, truth = good, bad, "A"
            quality[a], quality[b] = 1.0, 0.35
        else:
            a, b, truth = bad, good, "B"
            quality[a], quality[b] = 0.35, 1.0

        pairs.append(
            Pair(
                doc_id=f"j{index + 1:02d}",
                question=question,
                a=a,
                b=b,
                truth=truth,
            )
        )

    return pairs, quality


PAIRS, QUALITY = build()


def corpus() -> list[Pair]:
    return list(PAIRS)


def quality_of(text: str) -> float:
    return QUALITY.get(text, 0.5)


def _unit(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:13], 16) / float(16**13)


NOISE = 0.10
POSITION_BIAS = 0.35
COST_PER_CALL = 0.00010


class NoisyJudge:
    """A judge with a real signal, plus noise and a thumb on the scale."""

    name = "noisy-judge"

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

        first, second = _extract_pair(prompt)
        q_first = quality_of(first)
        q_second = quality_of(second)

        if q_first == q_second:
            verdict = "tie"
        else:
            verdict = "A" if q_first > q_second else "B"

        if _unit(prompt, "noise") < NOISE:
            verdict = {"A": "B", "B": "A"}.get(verdict, verdict)

        if _unit(prompt, "bias") < POSITION_BIAS:
            verdict = "A"

        text = f"Winner: {verdict}" if verdict in ("A", "B") else "Winner: tie"

        latency = 120.0 + 200.0 * _unit(prompt, "lat")
        self._cost += COST_PER_CALL
        self._latencies.append(latency)
        self.calls.append(
            {
                "cost_usd": COST_PER_CALL,
                "latency_ms": latency,
                "prompt_tail": prompt[-120:],
                "output": text,
            }
        )
        return Response(
            text=text,
            tokens_in=max(1, len(prompt) // 4),
            tokens_out=4,
            latency_ms=latency,
            cost_usd=COST_PER_CALL,
        )


def _extract_pair(prompt: str) -> tuple[str, str]:
    a = prompt.split("RESPONSE A:")[-1] if "RESPONSE A:" in prompt else ""
    if "RESPONSE B:" in a:
        a, b = a.split("RESPONSE B:", 1)
        return a.strip(), b.strip()
    return a.strip(), ""
