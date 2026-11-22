"""Drill 2 — retrieval."""

from __future__ import annotations

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import corpus as questions

NAME = "w02 - finding the right document"
PREMISE = "Rank 40 runbooks for 30 questions without an embedding model."
TARGET_ACCURACY = 0.88
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "retrieve"


def corpus() -> list:
    return questions()


def build_model(seed: int = 7):
    return ScriptedModel({})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    recall3 = 0
    first = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        question = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue
        ranked = result.prediction or []
        if not isinstance(ranked, list):
            crashes += 1
            modes["returned not a list"] = modes.get("returned not a list", 0) + 1
            continue

        if question.gold in ranked[:3]:
            recall3 += 1
        else:
            rank = ranked.index(question.gold) + 1 if question.gold in ranked else None
            cause = "not retrieved" if rank is None else f"ranked {rank}"
            modes[cause] = modes.get(cause, 0) + 1
            failures.append(
                {
                    "doc_id": question.doc_id,
                    "cause": cause,
                    "detail": question.text,
                    "expected": question.gold,
                    "predicted": ranked[:3],
                }
            )

        if ranked and ranked[0] == question.gold:
            first += 1

    metrics = {
        "recall@3": recall3 / n if n else 0.0,
        "first-hit": first / n if n else 0.0,
    }
    return make_card(
        metrics=metrics,
        model=model,
        n_items=n,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        crashes=crashes,
        modes=modes,
        failures=failures,
        notes=["retrieval needs no model calls; the whole cost is your index"],
    )
