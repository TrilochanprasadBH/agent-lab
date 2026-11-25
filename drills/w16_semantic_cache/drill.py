"""Drill 16 — the semantic cache."""

from __future__ import annotations

from agentlab.evals import Scorecard, percentile

from . import data

NAME = "w16 - a cache that reuses answers, and the threshold that decides"
PREMISE = "Serve repeat questions from a similarity cache without answering the wrong one."
TARGET_ACCURACY = 0.68
MAX_COST_USD = 0.40
SUPPORTS_REAL = False
TASK_NAME = "serve"


def corpus() -> list:
    return data.build()


def build_model(seed: int = 2027):
    return data.AnswerModel()


def score(results, model, target_accuracy: float, max_cost_usd: float):
    hits = served = wrong = invalid = misses = 0
    per_day: list[dict[str, float]] = []
    failures: list[dict] = []
    modes: dict[str, int] = {}

    for result in results:
        day = result.invoice
        payload = result.prediction if isinstance(result.prediction, dict) else {}
        decisions = payload.get("served") or []

        if result.crash:
            modes[f"crash: {result.crash.splitlines()[0][:50]}"] = (
                modes.get(f"crash: {result.crash.splitlines()[0][:50]}", 0) + 1
            )
            continue
        if len(decisions) != len(day.turns):
            modes["wrong number of decisions"] = modes.get("wrong number of decisions", 0) + 1
            continue

        seen: dict[str, int] = {}
        day_hits = day_wrong = day_served = 0
        for turn, decision in zip(day.turns, decisions):
            if decision is None:
                misses += 1
                seen[turn.id] = data.TRUTH[turn.id]
                continue

            if decision not in seen:
                invalid += 1
                modes["served a turn that had not arrived"] = (
                    modes.get("served a turn that had not arrived", 0) + 1
                )
                seen[turn.id] = data.TRUTH[turn.id]
                continue

            day_served += 1
            if seen[decision] == data.TRUTH[turn.id]:
                hits += 1
                day_hits += 1
            else:
                wrong += 1
                day_wrong += 1
                modes["served the wrong intent"] = modes.get("served the wrong intent", 0) + 1
                failures.append(
                    {
                        "doc_id": turn.id,
                        "cause": "wrong intent",
                        "detail": f"reused {decision} for {turn.text!r}",
                    }
                )
            seen[turn.id] = data.TRUTH[turn.id]

        served += day_served
        per_day.append(
            {
                "hits": day_hits,
                "wrong": day_wrong,
                "turns": len(day.turns),
            }
        )

    turns = sum(row["turns"] for row in per_day) or 1
    hit_rate = hits / turns
    wrong_rate = wrong / turns
    invalid_rate = invalid / turns

    # A policy that answers the wrong question is not a partial success. Exceeding the
    # wrong-hit budget scores zero, and the note says which rule fired.
    within_budget = wrong_rate <= data.WRONG_HIT_BUDGET and invalid_rate == 0.0
    accuracy = hit_rate if within_budget else 0.0

    held_out = per_day[data.TRAIN_DAYS:] or []
    held_turns = sum(row["turns"] for row in held_out) or 1
    held_hit = sum(row["hits"] for row in held_out) / held_turns if held_out else 0.0
    held_wrong = sum(row["wrong"] for row in held_out) / held_turns if held_out else 0.0

    notes = [
        f"{served} of {turns} turns served from cache, {misses} paid for",
        f"wrong hits {wrong_rate:.1%} (budget {data.WRONG_HIT_BUDGET:.0%})",
        f"held-out days {data.TRAIN_DAYS + 1}-{data.DAYS}: hit {held_hit:.1%}, wrong {held_wrong:.1%}",
    ]
    if not within_budget:
        notes.append("scored zero: the wrong-hit budget was exceeded")

    return Scorecard(
        accuracy=accuracy,
        per_field={
            "hit rate": hit_rate,
            "wrong hits": wrong_rate,
            "held-out hits": held_hit,
        },
        cost_usd=model.cost_usd,
        cost_per_doc=model.cost_usd / len(results) if results else 0.0,
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=model.n_calls,
        calls_per_doc=model.n_calls / len(results) if results else 0.0,
        crashes=sum(1 for result in results if result.crash),
        n_docs=len(results),
        failures=failures,
        modes=modes,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        min_calls_per_doc=1.0,
        notes=notes,
        hints_override=[
            "A zero hit rate means the cache key is the text. Key it on the embedding and set a "
            "threshold.",
            "Sweep the threshold on days 1-6 and read the wrong-hit column. Above the budget the "
            "run scores zero, so pick the highest hit rate that stays inside it.",
            "Do not drop the nearest-neighbour search when the cache is large; scan every cached "
            "turn and compare, then set the threshold.",
        ],
    )
