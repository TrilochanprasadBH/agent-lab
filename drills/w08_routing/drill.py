"""Drill 8 — routing by cost."""

from __future__ import annotations

from agentlab.evals import make_card

from .data import TieredModel, corpus as queries

NAME = "w08 \u00b7 routing and cost"
PREMISE = "Right is easy. Right for a third of the price is the actual job."
TARGET_ACCURACY = 0.92
MAX_COST_USD = 0.030
SUPPORTS_REAL = False
TASK_NAME = "answer"


def corpus() -> list:
    return queries()


def build_model(seed: int = 7):
    return TieredModel()


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    correct = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        query = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        payload = result.prediction if isinstance(result.prediction, dict) else {}
        answer = str(payload.get("answer", ""))
        ok = query.answer.casefold() in answer.casefold()

        if ok:
            correct += 1
        else:
            key = f"wrong on {query.difficulty}"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": query.doc_id,
                    "cause": key,
                    "detail": query.text,
                    "expected": query.answer,
                    "predicted": answer,
                }
            )

    return make_card(
        metrics={"correct": correct / n if n else 0.0},
        model=model,
        n_items=n,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        crashes=crashes,
        modes=modes,
        failures=failures,
        notes=[f"${model.cost_usd:.4f} spent; cap ${max_cost_usd:.4f}"],
    )
