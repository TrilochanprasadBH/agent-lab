"""Drill 20 — debug the wrong answer."""

from __future__ import annotations

from agentlab.evals import Scorecard, percentile

from . import data
from .data import STAGES

NAME = "w20 - finding the first stage where the evidence disappeared"
PREMISE = "Name the failing stage and the repair for 42 wrong answers, from the traces alone."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 0.0
SUPPORTS_REAL = False
TASK_NAME = "diagnose"


def corpus() -> list:
    return data.build()


def build_model(seed: int = 2027):
    return data.model()


def score(results, model, target_accuracy: float, max_cost_usd: float):
    total = joint = stage_right = fix_right = crashes = 0
    per_class = {stage: [0, 0] for stage in STAGES}
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        case = result.invoice
        if result.crash:
            crashes += 1
            modes[f"crash: {result.crash.split(':')[0]}"] = (
                modes.get(f"crash: {result.crash.split(':')[0]}", 0) + 1
            )

        prediction = result.prediction if isinstance(result.prediction, dict) else {}
        stage = str(prediction.get("stage", "")).strip().lower()
        fix = str(prediction.get("fix", "")).strip().lower()

        total += 1
        per_class[case.stage][1] += 1
        stage_right += stage == case.stage
        fix_right += fix == case.fix

        if stage == case.stage and fix == case.fix:
            joint += 1
            per_class[case.stage][0] += 1
            continue

        key = f"{case.stage} -> {stage or '(missing)'}"
        modes[key] = modes.get(key, 0) + 1
        failures.append(
            {
                "doc_id": case.id,
                "cause": key,
                "detail": case.question,
                "expected": f"{case.stage} / {case.fix}",
                "predicted": f"{stage or '(missing)'} / {fix or '(missing)'}",
            }
        )

    per_field: dict[str, float] = {}
    for stage in STAGES:
        hit, seen = per_class[stage]
        per_field[stage] = hit / seen if seen else 0.0
    per_field["stage right"] = stage_right / total if total else 0.0
    per_field["fix right"] = fix_right / total if total else 0.0

    return Scorecard(
        accuracy=joint / total if total else 0.0,
        per_field=per_field,
        cost_usd=model.cost_usd,
        cost_per_doc=0.0,
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=model.n_calls,
        calls_per_doc=0.0,
        crashes=crashes,
        n_docs=len(results),
        failures=failures,
        modes=modes,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        min_calls_per_doc=0.0,
        notes=[
            f"{len(results)} cases, {len(STAGES)} stages, "
            f"{len(results) // len(STAGES)} of each",
            "the answer is wrong in every case, including the ones where retrieval worked",
            "no model calls: this is a reading drill, so the cost cap is zero",
        ],
        hints_override=[
            "Group your misses by stage. If everything lands in `generation`, you are reading the "
            "symptom instead of walking the pipeline.",
            "For each case ask one question at a time, in this order: is the value in the index, "
            "in a single chunk, in the ranking, in the prompt, in the answer? Stop at the first no.",
            "Two stages share the symptom `the answer is wrong`: one where the value never reached "
            "the prompt, one where it reached the prompt and an older chunk outvoted it.",
            "Retrieval has two repairs. Where the gold sits decides which: a few places below k is "
            "`raise_k`, far below k is `hybrid`.",
        ],
    )
