"""Pull requests whose aggregate score improves while a category gets worse.

This is Simpson's paradox with a deploy button on it. One slice improves enough to
drag the average up; another slice quietly regresses. The aggregate says "better".
The regression is real, and it is in the category that a customer will find first.

The rule for this drill is stated in `spec.md`: ship only if the aggregate improves
by at least 2 points **and** no slice regresses by 2 points or more.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

SLICES = ("refunds", "international", "long-context")


@dataclass(frozen=True)
class PullRequest:
    doc_id: str
    title: str
    slices: dict[str, tuple[tuple[bool, bool], ...]]
    truth: str
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.title)


def _slice(rng: random.Random, n: int, base: float, delta: float) -> tuple[tuple[bool, bool], ...]:
    pairs = []
    for _ in range(n):
        before = rng.random() < base
        if rng.random() < 0.04:  # ordinary flake
            after = not before
        elif delta >= 0:
            after = before or (rng.random() < delta)
        else:
            after = before and not (rng.random() < -delta)
        pairs.append((before, after))
    return tuple(pairs)


def _rates(slices: dict[str, tuple[tuple[bool, bool], ...]]) -> tuple[float, float, dict[str, float]]:
    before = [b for pairs in slices.values() for b, _ in pairs]
    after = [a for pairs in slices.values() for _, a in pairs]
    agg_before = sum(before) / len(before)
    agg_after = sum(after) / len(after)
    per_slice = {
        name: (sum(a for _, a in pairs) - sum(b for b, _ in pairs)) / len(pairs)
        for name, pairs in slices.items()
    }
    return agg_before, agg_after, per_slice


def _rule(slices) -> str:
    agg_before, agg_after, per_slice = _rates(slices)
    if agg_after - agg_before >= 0.02 and min(per_slice.values()) >= -0.02:
        return "ship"
    return "block"


def build(seed: int = 2027) -> list[PullRequest]:
    rng = random.Random(seed)
    prs: list[PullRequest] = []
    counter = 0

    def add(title: str, slices: dict) -> None:
        nonlocal counter
        counter += 1
        prs.append(PullRequest(f"pr{counter:02d}", title, slices, _rule(slices)))

    # 12 genuinely good changes
    for _ in range(12):
        slices = {
            "refunds": _slice(rng, 24, 0.70, rng.uniform(0.12, 0.22)),
            "international": _slice(rng, 24, 0.60, 0.0),
            "long-context": _slice(rng, 24, 0.55, 0.0),
        }
        add(f"improve refund extraction (v{rng.randint(2, 9)})", slices)

    # 12 Simpson cases: aggregate up, one slice down
    for _ in range(12):
        slices = {
            "refunds": _slice(rng, 48, 0.65, rng.uniform(0.20, 0.32)),
            "international": _slice(rng, 24, 0.70, -rng.uniform(0.08, 0.16)),
            "long-context": _slice(rng, 24, 0.60, 0.0),
        }
        add(f"broad prompt rewrite, aggregate looks up (v{rng.randint(2, 9)})", slices)

    # 6 changes that moved nothing
    for _ in range(6):
        slices = {
            "refunds": _slice(rng, 24, 0.65, rng.uniform(-0.02, 0.02)),
            "international": _slice(rng, 24, 0.60, rng.uniform(-0.02, 0.02)),
            "long-context": _slice(rng, 24, 0.55, rng.uniform(-0.02, 0.02)),
        }
        add(f"formatting and comment cleanup (v{rng.randint(2, 9)})", slices)

    rng.shuffle(prs)
    return prs


CORPUS = build()


def corpus() -> list[PullRequest]:
    return list(CORPUS)


def rates(pr: PullRequest):
    return _rates(pr.slices)
