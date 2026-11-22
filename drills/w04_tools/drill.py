"""Drill 4 — tool arguments."""

from __future__ import annotations

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import corpus as cases

NAME = "w04 - turning text into a tool call"
PREMISE = "Turn 14 malformed tool calls into validated calls or named rejections."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "handle"

DANGEROUS = {"refund_order", "delete_account"}


def corpus() -> list:
    return cases()


def build_model(seed: int = 7):
    return ScriptedModel({case.request: [case.model_output] for case in cases()})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    correct = 0
    unsafe = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        case = result.invoice

        for entry in case.world.log:
            if entry["tool"] in DANGEROUS:
                unsafe += 1
                modes[f"unsafe: {entry['tool']} executed"] = (
                    modes.get(f"unsafe: {entry['tool']} executed", 0) + 1
                )

        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        prediction = result.prediction if isinstance(result.prediction, dict) else {}
        outcome = prediction.get("outcome")
        tool = prediction.get("tool")

        ok = outcome == case.expected
        if ok and case.expected == "ok":
            ok = tool == case.expected_tool

        if ok:
            correct += 1
        else:
            key = f"expected {case.expected}, got {outcome}"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": case.doc_id,
                    "cause": key,
                    "detail": case.model_output[:70],
                    "expected": case.expected,
                    "predicted": outcome,
                }
            )

    metrics = {
        "correct outcome": correct / n if n else 0.0,
        "safe": 1.0 if unsafe == 0 else 0.0,
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
        notes=[f"{unsafe} dangerous call(s) reached the world"],
    )
