"""Drill 23 — fine-tune, retrieve, or prompt."""

from __future__ import annotations

from agentlab.evals import Scorecard, percentile

from . import data
from .data import ANSWERS

NAME = "w23 - choosing between prompting, retrieval and a fine-tune"
PREMISE = "Pick the cheapest architecture that clears the bar, across 24 measured scenarios."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 0.0
SUPPORTS_REAL = False
TASK_NAME = "choose"

KINDS = ("cost", "constraint", "none")


def corpus() -> list:
    return data.build()


def build_model(seed: int = 2027):
    return data.model()


def score(results, model, target_accuracy: float, max_cost_usd: float):
    correct = 0
    crashes = 0
    per_kind = {kind: [0, 0] for kind in KINDS}
    per_answer = {answer: [0, 0] for answer in ANSWERS}
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        scenario = result.invoice
        truth = data.TRUTH[scenario.id]
        if result.crash:
            crashes += 1
            modes[f"crash: {result.crash.split(':')[0]}"] = (
                modes.get(f"crash: {result.crash.split(':')[0]}", 0) + 1
            )

        answer = str(result.prediction or "").strip().lower()
        per_kind[scenario.kind][1] += 1
        per_answer[truth][1] += 1
        if answer == truth:
            correct += 1
            per_kind[scenario.kind][0] += 1
            per_answer[truth][0] += 1
        else:
            modes[f"{truth} -> {answer or '(missing)'}"] = (
                modes.get(f"{truth} -> {answer or '(missing)'}", 0) + 1
            )
            failures.append(
                {
                    "doc_id": scenario.id,
                    "cause": f"chose {answer or 'nothing'}, expected {truth}",
                    "detail": scenario.summary,
                    "expected": truth,
                    "predicted": answer or "(missing)",
                }
            )

    n = len(results)
    per_field = {
        "decided by cost": per_kind["cost"][0] / per_kind["cost"][1] if per_kind["cost"][1] else 0.0,
        "by constraint": (
            per_kind["constraint"][0] / per_kind["constraint"][1]
            if per_kind["constraint"][1]
            else 0.0
        ),
        "bar not met": (
            per_kind["none"][0] / per_kind["none"][1] if per_kind["none"][1] else 0.0
        ),
    }

    notes = [
        f"{n} scenarios: {per_kind['cost'][1]} decided by cost, "
        f"{per_kind['constraint'][1]} by a constraint, {per_kind['none'][1]} by the bar",
        "fine-tuning is a fixed cost amortised over a volume, so the answer changes with scale",
        "no model calls: the decision is arithmetic over the scenario",
    ]

    return Scorecard(
        accuracy=correct / n if n else 0.0,
        per_field=per_field,
        cost_usd=0.0,
        cost_per_doc=0.0,
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=0,
        calls_per_doc=0.0,
        crashes=crashes,
        n_docs=n,
        failures=failures,
        modes=modes,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        min_calls_per_doc=0.0,
        notes=notes,
        hints_override=[
            "Three passes, in order: is the option possible, does it clear the bar, is it the "
            "cheapest per day. Skipping a pass is what the wrong answers have in common.",
            "Fine-tuning has a fixed cost and a per-request saving. At twenty requests a day the "
            "fixed cost dominates; at twenty thousand the saving does. Compute the crossover.",
            "A constraint can remove the cheapest option. Weekly-changing facts, a citation "
            "requirement and no labelled examples each rule out fine-tuning, for different "
            "reasons.",
            "When nothing clears the bar, the answer is `none`. Six of these scenarios end that "
            "way and shipping the least bad option is the failure the bar is there to catch.",
        ],
    )
