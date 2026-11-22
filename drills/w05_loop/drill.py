"""Drill 5 — the agent loop."""

from __future__ import annotations

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import corpus as cases

NAME = "w05 - running a multi-step task"
PREMISE = "Run 10 tasks to a correct stop, including stopping deliberately."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "solve"


def corpus() -> list:
    return cases()


def build_model(seed: int = 7):
    return ScriptedModel({case.request: list(case.script) for case in cases()})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    n = len(results)
    correct = 0
    in_budget = 0
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        case = result.invoice
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            continue

        out = result.prediction if isinstance(result.prediction, dict) else {}
        kind = out.get("kind")
        text = str(out.get("text", ""))
        steps = int(out.get("steps") or 0)

        if steps <= case.max_steps:
            in_budget += 1
        else:
            modes["over step budget"] = modes.get("over step budget", 0) + 1

        ok = kind == case.expect_kind
        if ok and case.expect_text:
            ok = case.expect_text.casefold() in text.casefold()
        if ok and steps > case.max_steps:
            ok = False

        if ok:
            correct += 1
        else:
            key = f"expected {case.expect_kind}, got {kind} ({steps} steps)"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": case.doc_id,
                    "cause": key,
                    "detail": case.request,
                    "expected": f"{case.expect_kind} {case.expect_text!r}".strip(),
                    "predicted": f"{kind} {text[:40]!r}",
                }
            )

    metrics = {"correct": correct / n if n else 0.0}
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
            "stopping deliberately is a correct answer, and it is scored as one",
            f"{in_budget}/{n} cases stayed inside the step budget",
        ],
    )
