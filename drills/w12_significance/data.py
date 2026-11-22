"""Two eval runs, and the question you will ask weekly:

    the number went up. Did anything actually happen?

Three kinds of scenario, and only one of them supports the word "better":

  - **paired, real**: same items, B genuinely fixes some of A's failures.
  - **paired, null**: same items, B differs only by noise.
  - **disjoint**: B was evaluated on a *different* item set, which happens to be
    easier. The aggregate looks better. Nothing was learned.

The third is the one that burns people, because the arithmetic is valid and the
conclusion is not.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Run:
    doc_id: str
    title: str
    a: dict[str, bool]
    b: dict[str, bool]
    truth: str  # "ship" | "no_ship"
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.title)


def build(seed: int = 2027) -> list[Run]:
    rng = random.Random(seed)
    runs: list[Run] = []
    counter = 0

    def add(title: str, a: dict[str, bool], b: dict[str, bool], truth: str) -> None:
        nonlocal counter
        counter += 1
        runs.append(Run(f"e{counter:02d}", title, a, b, truth))

    # -- paired, real improvement ------------------------------------------
    for _ in range(15):
        delta = rng.uniform(0.12, 0.28)
        a: dict[str, bool] = {}
        b: dict[str, bool] = {}
        for index in range(96):
            item = f"q{index:03d}"
            p = rng.uniform(0.30, 0.85)
            a[item] = rng.random() < p
            b[item] = a[item] or (rng.random() < delta)
        add(f"prompt v{rng.randint(2, 9)} vs current, same 96 items", a, b, "ship")

    # -- paired, null -------------------------------------------------------
    for _ in range(10):
        a, b = {}, {}
        for index in range(96):
            item = f"q{index:03d}"
            p = rng.uniform(0.30, 0.85)
            a[item] = rng.random() < p
            # flake in both directions, no systematic advantage
            b[item] = a[item] if rng.random() > 0.06 else (rng.random() < p)
        add(f"formatting tweak on the same 96 items", a, b, "no_ship")

    # -- disjoint item sets, B's set is easier ------------------------------
    for _ in range(10):
        a, b = {}, {}
        for index in range(96):
            item = f"q{index:03d}"
            a[item] = rng.random() < rng.uniform(0.30, 0.60)
            b[f"r{index:03d}"] = rng.random() < rng.uniform(0.55, 0.80)
        add("new prompt, evaluated on a freshly sampled question set", a, b, "no_ship")

    rng.shuffle(runs)
    return runs


CORPUS = build()


def corpus() -> list[Run]:
    return list(CORPUS)


def accuracy(run: Run) -> float:
    return sum(run.a.values()) / len(run.a)


def accuracy_b(run: Run) -> float:
    return sum(run.b.values()) / len(run.b)
