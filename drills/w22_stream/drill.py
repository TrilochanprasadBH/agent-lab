"""Drill 22 — streaming and disconnects."""

from __future__ import annotations

from agentlab.evals import Scorecard, percentile

from . import data
from .data import FAULTS

NAME = "w22 - finishing a stream that breaks"
PREMISE = "Recover the exact answer from 30 SSE streams that die mid-flight."
TARGET_ACCURACY = 0.95
MAX_COST_USD = 0.0026
SUPPORTS_REAL = False
TASK_NAME = "stream"


def corpus() -> list:
    return data.build()


def build_model(seed: int = 2027):
    cases = data.build()
    return data.fabric(cases)


def score(results, model, target_accuracy: float, max_cost_usd: float):
    exact = complete = both = 0
    per_fault = {fault: [0, 0] for fault in FAULTS}
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []
    n = len(results)

    for result in results:
        case = result.invoice
        stat = model.stats.get(case.id, {"connections": 0, "duplicates": 0, "tokens": 0})
        if result.crash:
            crashes += 1
            modes[f"crash: {result.crash.split(':')[0]}"] = (
                modes.get(f"crash: {result.crash.split(':')[0]}", 0) + 1
            )

        payload = result.prediction if isinstance(result.prediction, dict) else {}
        text = str(payload.get("text", ""))
        is_exact = text == case.gold
        is_complete = payload.get("complete") is True

        exact += is_exact
        complete += is_complete
        per_fault[case.fault][1] += 1
        if is_exact and is_complete:
            both += 1
            per_fault[case.fault][0] += 1

        if not (is_exact and is_complete):
            if not text:
                key = "returned nothing"
            elif text.startswith(case.gold) or case.gold.startswith(text):
                key = "truncated answer"
            elif case.gold in text:
                key = "duplicated tokens"
            else:
                key = "wrong text"
            modes[key] = modes.get(key, 0) + 1
            failures.append(
                {
                    "doc_id": case.id,
                    "cause": f"{key} / complete={is_complete}",
                    "detail": case.raw,
                    "expected": f"{len(case.tokens)} tokens",
                    "predicted": f"{len(text.split())} tokens, "
                    f"{stat['connections']} connection(s), "
                    f"{stat['duplicates']} duplicate(s)",
                }
            )

    notes = [
        f"{model.n_calls} connections for {n} streams "
        f"({model.n_calls / n:.2f} per stream), {model.cost_usd:.5f} spent",
        f"{sum(stat['duplicates'] for stat in model.stats.values())} token frames were "
        "delivered twice",
        "every stream breaks, so a client with no recovery path cannot finish any of them",
    ]

    return Scorecard(
        accuracy=both / n if n else 0.0,
        per_field={
            "exact text": exact / n if n else 0.0,
            "marked complete": complete / n if n else 0.0,
            "both": both / n if n else 0.0,
            **{
                fault.replace("_", " "): (hit / seen if seen else 0.0)
                for fault, (hit, seen) in per_fault.items()
            },
        },
        cost_usd=model.cost_usd,
        cost_per_doc=model.cost_usd / n if n else 0.0,
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=model.n_calls,
        calls_per_doc=model.n_calls / n if n else 0.0,
        crashes=crashes,
        n_docs=n,
        failures=failures,
        modes=modes,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        min_calls_per_doc=1.0,
        notes=notes,
        hints_override=[
            "Group your failures by fault type. If `cut` and `eof` fail together, you are "
            "treating the end of the socket as the end of the answer.",
            "The terminator is the only evidence that the answer finished. Without it, reconnect "
            "even though you cannot tell how much is missing.",
            "`resume_from` is exclusive and the server may ignore it. Append only ids greater "
            "than the last one you accepted; that makes a replay free instead of fatal.",
            "Restarting from scratch is correct and costs twice as much. Check the cost line, "
            "not just the accuracy line.",
        ],
    )
