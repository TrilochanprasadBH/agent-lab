"""Drill 10 — trace triage."""

from __future__ import annotations

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import corpus as traces

NAME = "w10 - naming the cause of a failure"
PREMISE = "Assign the correct root cause to 60 traces full of misleading lines."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "classify"


def corpus() -> list:
    return traces()


def build_model(seed: int = 7):
    return ScriptedModel({})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    correct = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        trace = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        label = str(result.prediction or "")
        if label == trace.truth:
            correct += 1
        else:
            key = f"{trace.truth} -> {label}"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": trace.doc_id,
                    "cause": key,
                    "detail": trace.text.splitlines()[-1],
                    "expected": trace.truth,
                    "predicted": label,
                }
            )

    return make_card(
        metrics={"correct cause": correct / n if n else 0.0},
        model=model,
        n_items=n,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        crashes=crashes,
        modes=modes,
        failures=failures,
        notes=["triage is a classification problem; ordering your rules matters more than adding them"],
    )
