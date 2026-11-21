"""Runs your task over a drill corpus and produces a scorecard."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

from .evals import Scorecard, score
from .model import SimModel


@dataclass
class Result:
    invoice: Any
    prediction: Any
    crash: str | None = None
    elapsed_ms: float = 0.0


def run_drill(
    corpus: list,
    task: Callable[[str, SimModel], dict],
    model: SimModel,
    *,
    target_accuracy: float = 0.90,
    max_cost_usd: float = 0.03,
) -> tuple[Scorecard, list[Result]]:
    model.reset()
    results: list[Result] = []

    for invoice in corpus:
        started = time.perf_counter()
        crash = None
        try:
            prediction = task(invoice.raw, model)
        except Exception as exc:  # noqa: BLE001 — crashes are scored, not swallowed
            prediction = {}
            crash = f"{type(exc).__name__}: {exc}"
        elapsed = (time.perf_counter() - started) * 1000
        results.append(
            Result(invoice=invoice, prediction=prediction, crash=crash, elapsed_ms=elapsed)
        )

    card = score(
        results,
        model,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
    )
    return card, results
