"""Drill 15 — regression gating."""

from __future__ import annotations

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import corpus as prs

NAME = "w15 - gating a release on every category"
PREMISE = "Gate 30 pull requests on per-category results, not the average."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "gate"


def corpus() -> list:
    return prs()


def build_model(seed: int = 7):
    return ScriptedModel({})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    correct = 0
    false_ship = 0
    false_block = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        pr = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        payload = result.prediction if isinstance(result.prediction, dict) else {}
        decision = "ship" if payload.get("ship") else "block"

        if decision == pr.truth:
            correct += 1
        else:
            if decision == "ship":
                false_ship += 1
                modes["shipped a regressed category"] = modes.get("shipped a regressed category", 0) + 1
            else:
                false_block += 1
                modes["blocked a good change"] = modes.get("blocked a good change", 0) + 1
            failures.append(
                {
                    "doc_id": pr.doc_id,
                    "cause": f"said {decision}",
                    "detail": pr.title,
                    "expected": pr.truth,
                    "predicted": decision,
                }
            )

    return make_card(
        metrics={"correct decisions": correct / n if n else 0.0},
        model=model,
        n_items=n,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        crashes=crashes,
        modes=modes,
        failures=failures,
        notes=[
            f"{false_ship} false ships, {false_block} false blocks",
            "a false ship reaches users; a false block costs an hour",
        ],
    )
