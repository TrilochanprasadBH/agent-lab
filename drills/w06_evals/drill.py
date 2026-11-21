"""Drill 6 — evals that generalise."""

from __future__ import annotations

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import corpus as test_items, hidden_labels

NAME = "w06 \u00b7 evals that resist overfitting"
PREMISE = "The train set is rigged. The test set is not. Only one of them is real."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "grade"


def corpus() -> list:
    return test_items()


def build_model(seed: int = 7):
    return ScriptedModel({})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    labels = hidden_labels()
    n = len(results)
    correct = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        reply = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        predicted = bool(result.prediction)
        truth = labels[reply.doc_id] == 1
        if predicted == truth:
            correct += 1
        else:
            key = "false positive" if predicted else "false negative"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": reply.doc_id,
                    "cause": key,
                    "detail": reply.text[:80],
                    "expected": truth,
                    "predicted": predicted,
                }
            )

    return make_card(
        metrics={"agreement": correct / n if n else 0.0},
        model=model,
        n_items=n,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        crashes=crashes,
        modes=modes,
        failures=failures,
        notes=["score is on the held-out split only; the train score is not measured"],
    )
