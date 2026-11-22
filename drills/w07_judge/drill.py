"""Drill 7 — judge calibration."""

from __future__ import annotations

from agentlab.evals import make_card

from .data import NoisyJudge, corpus as pairs

NAME = "w07 - calibrating a noisy judge"
PREMISE = "Cancel a judge's position bias and outvote its noise within budget."
TARGET_ACCURACY = 0.85
MAX_COST_USD = 0.015
SUPPORTS_REAL = False
TASK_NAME = "judge"


def corpus() -> list:
    return pairs()


def build_model(seed: int = 7):
    return NoisyJudge()


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    correct = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        pair = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        verdict = str(result.prediction or "").strip()
        if verdict == pair.truth:
            correct += 1
        else:
            key = f"truth {pair.truth}, said {verdict}"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": pair.doc_id,
                    "cause": key,
                    "detail": pair.question,
                    "expected": pair.truth,
                    "predicted": verdict,
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
        notes=[f"{model.n_calls} calls for {n} pairs"],
    )
