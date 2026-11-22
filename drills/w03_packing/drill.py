"""Drill 3 — context packing."""

from __future__ import annotations

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import BUDGET_TOKENS, corpus as questions, count_tokens

NAME = "w03 - fitting evidence into a budget"
PREMISE = "Fit the evidence for each question into a 120-word budget."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "pack"


def corpus() -> list:
    return questions()


def build_model(seed: int = 7):
    return ScriptedModel({})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    covered = 0
    within = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        question = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        context = result.prediction or ""
        if not isinstance(context, str):
            crashes += 1
            modes["returned not a string"] = modes.get("returned not a string", 0) + 1
            continue

        tokens = count_tokens(context)
        if tokens <= BUDGET_TOKENS:
            within += 1
        else:
            modes[f"over budget (+{tokens - BUDGET_TOKENS})"] = (
                modes.get(f"over budget (+{tokens - BUDGET_TOKENS})", 0) + 1
            )

        missing = [probe for probe in question.probes if probe.casefold() not in context.casefold()]
        if not missing and tokens <= BUDGET_TOKENS:
            covered += 1
        else:
            key = "missing evidence" if missing else "over budget"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": question.doc_id,
                    "cause": key,
                    "detail": f"{question.text}  [{tokens} tokens]",
                    "expected": list(question.probes),
                    "predicted": missing or ["(over budget)"],
                }
            )

    metrics = {"evidence coverage": covered / n if n else 0.0}
    return make_card(
        metrics=metrics,
        model=model,
        n_items=n,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        crashes=crashes,
        modes=modes,
        failures=failures,
        notes=[
            f"budget is {BUDGET_TOKENS} whitespace tokens per answer",
            f"{within}/{n} packs stayed within budget",
        ],
    )
