"""Runs your task over a drill corpus, one item at a time.

Scoring is deliberately *not* here. A drill knows what its numbers mean, so
each `drills/wNN/drill.py` exposes a `score(results, model, target, cap)`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Result:
    invoice: Any  # the corpus item; drills name it `invoice` for historical reasons
    prediction: Any
    crash: str | None = None
    elapsed_ms: float = 0.0


def run_drill(
    corpus: list,
    task: Callable[..., Any],
    model,
) -> list[Result]:
    """Call `task(item, model)` for every item, capturing crashes as data."""
    model.reset()
    results: list[Result] = []

    for item in corpus:
        started = time.perf_counter()
        crash = None
        try:
            prediction = task(item, model)
        except Exception as exc:  # noqa: BLE001 — crashes are scored, not swallowed
            prediction = None
            crash = f"{type(exc).__name__}: {exc}"
        elapsed = (time.perf_counter() - started) * 1000
        results.append(
            Result(invoice=item, prediction=prediction, crash=crash, elapsed_ms=elapsed)
        )

    return results
