"""A pool of candidate eval items, most of which you should not use.

Two things are wrong with simply taking the first N:

  - the pool is sorted by topic, so the first N covers two tags and one difficulty;
  - some items are near-duplicates of each other, so two slots buy one piece of
    information.

An eval set is a *sample*, and a sample that misses whole categories cannot tell
you that those categories broke.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

TAGS = (
    "refund", "billing", "retrieval", "tools", "auth",
    "long-context", "adversarial", "multi-hop",
)
DIFFICULTIES = ("easy", "hard")
PER_CELL = 2  # how many items each (tag, difficulty) cell needs


@dataclass(frozen=True)
class Item:
    doc_id: str
    tag: str
    difficulty: str
    source: str  # several items can come from the same source document
    question: str
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.question)


def build(seed: int = 2027) -> list[Item]:
    rng = random.Random(seed)
    items: list[Item] = []
    counter = 0

    # Sorted by tag on purpose: the lazy slice is biased.
    for tag in TAGS:
        for difficulty in DIFFICULTIES:
            for _ in range(15):
                counter += 1
                source = f"kb-{tag[:3]}-{difficulty[0]}-{rng.randint(1, 6):02d}"
                items.append(
                    Item(
                        doc_id=f"i{counter:03d}",
                        tag=tag,
                        difficulty=difficulty,
                        source=source,
                        question=f"[{tag}/{difficulty}] question about {tag} ({source})",
                    )
                )

    return items


POOL = build()


def corpus() -> list:
    """The pool is the same for every run; the task selects from it."""
    return [POOL]


def cells() -> list[tuple[str, str]]:
    return [(tag, difficulty) for tag in TAGS for difficulty in DIFFICULTIES]
