"""Drill 16 — the semantic cache, and the threshold nobody can pick for you.

A support assistant answers the same forty questions in different words, all day. A cache keyed
on exact text almost never hits. A cache keyed on embedding similarity hits often — including
when it should not, because two different questions can sit closer together than two
paraphrases of one question.

The world here is synthetic and says so. Embeddings are points in 48 dimensions: a cluster
centre per intent, and paraphrases placed near it. Six pairs of intents are placed at 0.96
similarity to each other, which is the trap. A real encoder's errors are not Gaussian, so the
absolute numbers do not transfer; what transfers is the decision, and the shape of the curve.

    threshold   hit rate   wrong hits
      0.80        68%         15%
      0.88        73.5%        4%
      0.90        60%          1.5%
      0.94         1%          0%

There is no threshold that maximises both. You pick a point on that curve by asking what a
wrong answer costs relative to a missed cache.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

DIMENSIONS = 48
INTENTS = 40
PARAPHRASES = 5
DAYS = 8
TRAIN_DAYS = 6
TRAP_PAIRS = 6
TRAP_COSINE = 0.96
PARAPHRASE_NOISE = 0.31
SEED = 2027

# What a wrong answer costs, relative to a missed cache. The drill states its own value: one
# wrong answer is treated as twenty missed caches, so the wrong-hit budget is 5%.
WRONG_HIT_BUDGET = 0.05


def _unit(vector: list[float]) -> tuple[float, ...]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return tuple(value / norm for value in vector)


def _noise(rng: random.Random) -> list[float]:
    return [rng.gauss(0.0, 1.0) for _ in range(DIMENSIONS)]


def cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right))


@dataclass(frozen=True)
class Turn:
    """One incoming question. No intent label: the cache has to infer it from the vector."""

    id: str
    text: str
    embedding: tuple[float, ...]


@dataclass(frozen=True)
class Day:
    """One day of traffic, in arrival order."""

    id: str
    turns: tuple[Turn, ...]
    raw: str = ""


# Intent labels, kept out of the items so a task cannot read the answer off the input.
TRUTH: dict[str, int] = {}

PHRASINGS = (
    "how do i {verb} a {noun}",
    "{verb}ing a {noun} seems wrong",
    "what should happen when i {verb} the {noun}",
    "my {noun} will not {verb}",
    "is there a way to {verb} this {noun}",
)

TOPICS = (
    ("cancel", "order"), ("cancel", "subscription"), ("refund", "order"),
    ("refund", "invoice"), ("resend", "invoice"), ("change", "address"),
    ("change", "card"), ("delete", "account"), ("export", "data"),
    ("reset", "password"), ("verify", "email"), ("upgrade", "plan"),
    ("downgrade", "plan"), ("pause", "subscription"), ("resume", "subscription"),
    ("track", "parcel"), ("return", "item"), ("exchange", "item"),
    ("report", "damage"), ("claim", "warranty"), ("apply", "discount"),
    ("remove", "discount"), ("add", "user"), ("remove", "user"),
    ("transfer", "ownership"), ("merge", "account"), ("split", "payment"),
    ("postpone", "delivery"), ("redirect", "parcel"), ("gift", "order"),
    ("cancel", "preorder"), ("refund", "shipping"), ("dispute", "charge"),
    ("update", "tax"), ("download", "receipt"), ("close", "ticket"),
    ("reopen", "ticket"), ("escalate", "ticket"), ("assign", "ticket"),
    ("archive", "ticket"),
)


def build(seed: int = SEED) -> list[Day]:
    rng = random.Random(seed)
    centres = [_unit(_noise(rng)) for _ in range(INTENTS)]

    # Trap pairs: the second intent is a different question whose centre is 0.96 from the first.
    for index in range(0, TRAP_PAIRS * 2, 2):
        jitter = _unit(_noise(rng))
        centres[index + 1] = _unit(
            [TRAP_COSINE * a + math.sqrt(1 - TRAP_COSINE**2) * b
             for a, b in zip(centres[index], jitter)]
        )

    pool: list[tuple[int, str, tuple[float, ...]]] = []
    counter = 0
    for intent, centre in enumerate(centres):
        verb, noun = TOPICS[intent % len(TOPICS)]
        for variant in range(PARAPHRASES):
            counter += 1
            text = PHRASINGS[variant % len(PHRASINGS)].format(verb=verb, noun=noun)
            embedding = _unit(
                [0.95 * a + PARAPHRASE_NOISE * b for a, b in zip(centre, _unit(_noise(rng)))]
            )
            pool.append((intent, text, embedding))

    days: list[Day] = []
    for day in range(DAYS):
        rng.shuffle(pool)
        turns: list[Turn] = []
        for position, (intent, text, embedding) in enumerate(pool[:200]):
            turn_id = f"d{day + 1}-{position:03d}"
            TRUTH[turn_id] = intent
            turns.append(Turn(id=turn_id, text=text, embedding=embedding))
        days.append(Day(id=f"day-{day + 1}", turns=tuple(turns), raw=f"day {day + 1}"))
    return days


def train_days() -> list[Day]:
    """The days you are allowed to tune on. The rest are held out."""
    return build()[:TRAIN_DAYS]


def test_days() -> list[Day]:
    return build()[TRAIN_DAYS:]


@dataclass
class Response:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float

    def __str__(self) -> str:
        return self.text


class AnswerModel:
    """The model a cache exists to avoid calling.

    It is a cost meter with a text output. It cannot see the intent, so its answer is a canned
    string — which is correct for this drill: what matters is how often you have to call it.
    """

    name = "answer-model"

    def __init__(self, *, cost_per_call: float = 0.0004) -> None:
        self.cost_per_call = cost_per_call
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

    def complete(self, prompt: str, system: str | None = None) -> Response:
        latency = 400.0 + (len(prompt) % 53)
        self._cost += self.cost_per_call
        self._latencies.append(latency)
        self.calls.append(
            {
                "tokens_in": max(1, len(prompt) // 4),
                "tokens_out": 24,
                "cost_usd": self.cost_per_call,
                "latency_ms": latency,
                "prompt_tail": prompt[-120:],
                "output": "Thanks for getting in touch. Here is what to do.",
            }
        )
        return Response(
            text="Thanks for getting in touch. Here is what to do.",
            tokens_in=max(1, len(prompt) // 4),
            tokens_out=24,
            latency_ms=latency,
            cost_usd=self.cost_per_call,
        )
