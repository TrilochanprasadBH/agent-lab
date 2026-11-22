"""Drill 14 — trajectory evaluation."""

from __future__ import annotations

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import corpus as traces

NAME = "w14 \u00b7 trajectory evaluation"
PREMISE = "The rubric is easy. Applying it the same way every time is not."
TARGET_ACCURACY = 0.85
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "score"

TOLERANCE = 1


def corpus() -> list:
    return traces()


def build_model(seed: int = 7):
    return ScriptedModel({})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    within = 0
    crashes = 0
    total_error = 0.0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        trace = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        try:
            predicted = int(result.prediction)
        except (TypeError, ValueError):
            crashes += 1
            modes["non-integer score"] = modes.get("non-integer score", 0) + 1
            continue

        error = abs(predicted - trace.truth)
        total_error += error

        if error <= TOLERANCE:
            within += 1
        else:
            key = f"{trace.archetype}: scored {predicted}, truth {trace.truth}"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": trace.doc_id,
                    "cause": trace.archetype,
                    "detail": trace.text.splitlines()[-1],
                    "expected": trace.truth,
                    "predicted": predicted,
                }
            )

    return make_card(
        metrics={"within 1 point": within / n if n else 0.0},
        model=model,
        n_items=n,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        crashes=crashes,
        modes=modes,
        failures=failures,
        notes=[f"mean absolute error {total_error / n:.2f} points" if n else ""],
    )
