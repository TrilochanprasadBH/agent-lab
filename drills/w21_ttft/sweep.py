#!/usr/bin/env python3
"""Compare the ways to serve the same 2,400 requests, and sweep the batch window.

    python3 drills/w21_ttft/sweep.py

Three gates: answer quality at least 92%, p95 time-to-first-token under 900ms, and cost under
$0.0008 per request. A policy that misses any of them is not a policy.

The first table shows that each knob fixes one gate and can break another. The second shows the
batch window on its own, because it is the only lever here whose best value is neither end of its
range: too short and the strong tier's queue grows, too long and every request pays the wait.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from drills.w21_ttft import data  # noqa: E402
from drills.w21_ttft.data import (  # noqa: E402
    COST_CAP_USD,
    QUALITY_TARGET,
    TTFT_BUDGET_MS,
)


def evaluate(decide, wait: float) -> dict:
    requests = data.build()
    decisions = {request.id: decide(request) for request in requests}
    outcomes = data.simulate(requests, decisions, wait)
    n = len(outcomes)
    ttfts = sorted(outcome.ttft_ms for outcome in outcomes)
    quality = sum(outcome.correct for outcome in outcomes) / n
    per_request = sum(outcome.cost_usd for outcome in outcomes) / n
    p95 = ttfts[int(0.95 * (n - 1))]
    fails = []
    if quality < QUALITY_TARGET:
        fails.append("quality")
    if p95 > TTFT_BUDGET_MS:
        fails.append("latency")
    if per_request > COST_CAP_USD:
        fails.append("cost")
    return {
        "quality": quality,
        "p50": ttfts[n // 2],
        "p95": p95,
        "cost": per_request,
        "batch": sum(outcome.batch_size for outcome in outcomes) / n,
        "truncated": sum(not outcome.evidence_kept for outcome in outcomes),
        "fails": fails,
    }


FAST = lambda request: "fast"  # noqa: E731
STRONG = lambda request: "strong"  # noqa: E731
ROUTE = lambda request: "strong" if request.hard else "fast"  # noqa: E731

POLICIES = (
    ("strong, no batch", STRONG, False, 99999, 400),
    ("strong, batch", STRONG, True, 99999, 400),
    ("fast, batch", FAST, True, 99999, 400),
    ("route, no batch", ROUTE, False, 99999, 400),
    ("route, batch, 200ms", ROUTE, True, 99999, 200),
    ("route, batch, 400ms", ROUTE, True, 99999, 400),
    ("route, batch, truncate 700", ROUTE, True, 700, 400),
)


def main() -> int:
    print()
    print(
        f" {data.N_REQUESTS} requests in {data.WINDOW_MS / 1000:.0f}s "
        f"({data.N_REQUESTS / (data.WINDOW_MS / 1000):.0f} rps), "
        f"{data.SLOTS} batch slots, batch max {data.BATCH_MAX}"
    )
    print(
        f" gates: quality >= {QUALITY_TARGET:.0%}, p95 <= {TTFT_BUDGET_MS:.0f}ms, "
        f"cost <= ${COST_CAP_USD:.4f}/request"
    )
    print()
    print(
        f" {'policy':<28}{'quality':>8}{'p50':>7}{'p95':>9}{'$/req':>10}"
        f"{'batch':>7}  {'fails':<18}"
    )
    for name, tier, batch, cap, wait in POLICIES:
        decide = lambda request, tier=tier, batch=batch, cap=cap: {  # noqa: E731
            "tier": tier(request),
            "batch": batch,
            "batch_wait_ms": wait,
            "max_prompt_tokens": min(request.prompt_tokens, cap),
        }
        row = evaluate(decide, wait)
        print(
            f" {name:<28}{row['quality']:>8.1%}{row['p50']:>7.0f}{row['p95']:>9.0f}"
            f"{row['cost']:>10.6f}{row['batch']:>7.1f}  "
            f"{', '.join(row['fails']) if row['fails'] else 'nothing'}"
        )
    print()

    print(" the batch window, with routing and no truncation")
    print()
    print(f" {'window':>7}{'quality':>9}{'p50':>7}{'p95':>9}{'$/req':>10}{'batch':>7}")
    for wait in (50, 100, 200, 300, 400, 600, 800, 1200):
        decide = lambda request, wait=wait: {  # noqa: E731
            "tier": ROUTE(request),
            "batch": True,
            "batch_wait_ms": wait,
            "max_prompt_tokens": request.prompt_tokens,
        }
        row = evaluate(decide, wait)
        print(
            f" {wait:>5}ms{row['quality']:>9.1%}{row['p50']:>7.0f}{row['p95']:>9.0f}"
            f"{row['cost']:>10.6f}{row['batch']:>7.1f}"
        )
    print()
    print(" the strong tier takes 30% of 40 rps. A window shorter than its inter-arrival time")
    print(" gives it batches of two or three, which is less than its capacity, so its queue")
    print(" grows for the whole minute and the p95 becomes the backlog.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
