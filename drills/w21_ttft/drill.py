"""Drill 21 — first-token latency under a three-way budget."""

from __future__ import annotations

from agentlab.evals import Scorecard, percentile

from . import data
from .data import (
    COST_CAP_USD,
    N_REQUESTS,
    QUALITY_TARGET,
    TTFT_BUDGET_MS,
)

NAME = "w21 - first-token latency is a queueing problem"
PREMISE = "Serve 2,400 requests at 40 rps: keep quality, p95 TTFT and cost at once."
TARGET_ACCURACY = QUALITY_TARGET
MAX_COST_USD = COST_CAP_USD * N_REQUESTS
SUPPORTS_REAL = False
TASK_NAME = "decide"

DEFAULT_WAIT_MS = 200.0


def corpus() -> list:
    return data.build()


def build_model(seed: int = 2027):
    return data.model()


def score(results, model, target_accuracy: float, max_cost_usd: float):
    requests = [result.invoice for result in results]
    decisions = {}
    crashes = 0
    modes: dict[str, int] = {}

    for result in results:
        if result.crash:
            crashes += 1
            modes[f"crash: {result.crash.split(':')[0]}"] = (
                modes.get(f"crash: {result.crash.split(':')[0]}", 0) + 1
            )
        decisions[result.invoice.id] = (
            result.prediction if isinstance(result.prediction, dict) else {}
        )

    waits = {
        decision.get("batch_wait_ms", DEFAULT_WAIT_MS)
        for decision in decisions.values()
    }
    if len(waits) > 1:
        modes["the batch window varied between requests"] = 1
    wait = min(waits) if waits else DEFAULT_WAIT_MS

    outcomes = data.simulate(requests, decisions, wait)
    n = len(outcomes)

    if n != len(requests):
        modes["the simulation dropped requests"] = len(requests) - n

    quality = sum(outcome.correct for outcome in outcomes) / n if n else 0.0
    easy = [o for o in outcomes if not o.request.hard]
    hard = [o for o in outcomes if o.request.hard]
    easy_quality = sum(o.correct for o in easy) / len(easy) if easy else 0.0
    hard_quality = sum(o.correct for o in hard) / len(hard) if hard else 0.0
    ttfts = [outcome.ttft_ms for outcome in outcomes]
    p50 = percentile(ttfts, 0.50)
    p95 = percentile(ttfts, 0.95)
    p99 = percentile(ttfts, 0.99)
    within = sum(1 for value in ttfts if value <= TTFT_BUDGET_MS) / n if n else 0.0
    batched = sum(1 for outcome in outcomes if outcome.batch_size > 1) / n if n else 0.0
    kept = sum(1 for outcome in outcomes if outcome.evidence_kept) / n if n else 0.0
    cost = sum(outcome.cost_usd for outcome in outcomes)
    per_request = cost / n if n else 0.0

    for outcome in outcomes:
        if outcome.error:
            modes[outcome.error] = modes.get(outcome.error, 0) + 1
        elif not outcome.correct:
            if not outcome.evidence_kept:
                modes["the gold evidence was truncated away"] = (
                    modes.get("the gold evidence was truncated away", 0) + 1
                )
            elif outcome.request.hard and outcome.tier == "fast":
                modes["a hard request went to the fast model"] = (
                    modes.get("a hard request went to the fast model", 0) + 1
                )

    failures = [
        {
            "doc_id": outcome.request.id,
            "cause": (
                "evidence truncated"
                if not outcome.evidence_kept
                else f"wrong answer on {outcome.tier}"
            ),
            "detail": outcome.request.raw,
            "expected": "correct",
            "predicted": f"{outcome.tier}, ttft {outcome.ttft_ms:.0f}ms, "
            f"batch {outcome.batch_size}",
        }
        for outcome in outcomes
        if not outcome.correct
    ][:8]

    over_latency = p95 > TTFT_BUDGET_MS
    over_cost = per_request > COST_CAP_USD
    scored = 0.0 if (over_latency or over_cost) else quality

    notes = [
        f"p50 {p50:.0f}ms, p95 {p95:.0f}ms, p99 {p99:.0f}ms against a {TTFT_BUDGET_MS:.0f}ms budget",
        f"${per_request:.6f} per request against a ${COST_CAP_USD:.4f} cap "
        f"({batched:.0%} of requests were batched)",
        f"quality {quality:.1%} against a {QUALITY_TARGET:.0%} target",
    ]
    if over_latency:
        notes.append(
            f"scored zero: p95 is {p95 / TTFT_BUDGET_MS:.1f}x the latency budget"
            + (" — the queue never recovers" if p95 > 10 * TTFT_BUDGET_MS else "")
        )
    if over_cost:
        notes.append(f"scored zero: cost is {per_request / COST_CAP_USD:.1f}x the cap")

    return Scorecard(
        accuracy=scored,
        per_field={
            "answer quality": quality,
            "easy requests": easy_quality,
            "hard requests": hard_quality,
            "within TTFT budget": within,
            "batched": batched,
            "evidence kept": kept,
        },
        cost_usd=cost,
        cost_per_doc=per_request,
        p95_latency_ms=p95,
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
            "Read the three gates separately. One of them is failing by two orders of "
            "magnitude, and that is a capacity problem, not a tuning problem.",
            "At 40 requests per second one pass per request cannot keep up. A batch shares one "
            "pass, and the pass costs the longest request in it — so the batch size is the "
            "throughput.",
            "The batch window is a lever with two ends: too short and the strong model's queue "
            "grows, too long and every request waits for it.",
            "Truncating the prompt lowers p95 by tens of milliseconds and destroys the evidence. "
            "Check what it does to the quality gate before you keep it.",
        ],
    )
