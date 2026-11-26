#!/usr/bin/env python3
"""Check the simulation, not a set of labels.

    python3 drills/w21_ttft/check_sim.py

There are no labels here — the world is generated — so what needs checking is that the world is
the one the lesson describes:

1. 2,400 requests arrive inside a 60-second window, in order, at 40 per second
2. 30% of them are hard, and every request carries its evidence inside its own prompt
3. the simulation returns one outcome per request, never serves a request before it arrives,
   never puts more than BATCH_MAX in a batch, and is deterministic
4. the batch window's cliff matches the capacity arithmetic: the strong tier needs a batch of
   2.8 to keep up, which at its arrival rate is a 236ms window, and the measured p95 collapses
   somewhere between 200ms and 300ms
5. the baseline fails at least two gates and the reference clears all three
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import importlib.util  # noqa: E402

from drills.w21_ttft import data  # noqa: E402
from drills.w21_ttft.data import (  # noqa: E402
    BATCH_MAX,
    COST_CAP_USD,
    DECODE_MS,
    PREFILL_MS,
    QUALITY_TARGET,
    SLOTS,
    TTFT_BUDGET_MS,
)

ROOT = Path(__file__).resolve().parents[2]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(decide, wait: float) -> dict:
    requests = data.build()
    world = data.model()
    decisions = {request.id: decide(request, world) for request in requests}
    outcomes = data.simulate(requests, decisions, wait)
    n = len(outcomes)
    ttfts = sorted(outcome.ttft_ms for outcome in outcomes)
    return {
        "outcomes": outcomes,
        "quality": sum(outcome.correct for outcome in outcomes) / n,
        "p95": ttfts[int(0.95 * (n - 1))],
        "cost": sum(outcome.cost_usd for outcome in outcomes) / n,
    }


def main() -> int:
    requests = data.build()
    problems: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    check(len(requests) == data.N_REQUESTS, f"{len(requests)} requests, expected {data.N_REQUESTS}")
    arrivals = [request.arrival_ms for request in requests]
    check(arrivals == sorted(arrivals), "arrivals are not in order")
    check(all(0 <= value <= data.WINDOW_MS for value in arrivals), "an arrival is outside the window")
    rate = data.N_REQUESTS / (data.WINDOW_MS / 1000)
    check(abs(rate - 40) < 0.5, f"the arrival rate is {rate:.1f} rps, not 40")

    hard = sum(1 for request in requests if request.hard)
    check(0.28 <= hard / len(requests) <= 0.32, f"{hard} hard requests is not close to 30%")
    for request in requests:
        check(
            request.gold_at + data.GOLD_TOKENS <= request.prompt_tokens,
            f"{request.id}: the evidence does not fit in its own prompt",
        )
        check(request.output_tokens > 0, f"{request.id}: no output tokens")

    wait = 400.0
    reference = load("w21_ref", ROOT / "solutions" / "w21_reference.py")
    baseline = load("w21_task", ROOT / "drills" / "w21_ttft" / "task.py")
    first = evaluate(reference.decide, wait)
    second = evaluate(reference.decide, wait)
    outcomes = first["outcomes"]

    check(len(outcomes) == len(requests), "the simulation dropped or duplicated requests")
    check(
        all(outcome.ttft_ms > 0 for outcome in outcomes),
        "a request was served before it arrived",
    )
    check(
        max(outcome.batch_size for outcome in outcomes) <= BATCH_MAX,
        f"a batch exceeded {BATCH_MAX}",
    )
    check(
        [outcome.ttft_ms for outcome in outcomes]
        == [outcome.ttft_ms for outcome in second["outcomes"]],
        "the simulation is not deterministic",
    )

    # The capacity arithmetic behind the window's cliff.
    strong_service = sum(
        PREFILL_MS["strong"] * request.prompt_tokens + DECODE_MS["strong"] * request.output_tokens
        for request in requests
    ) / len(requests)
    throughput_per_batch = SLOTS / (sum(
        PREFILL_MS["strong"] * request.prompt_tokens + DECODE_MS["strong"] * request.output_tokens
        for request in requests
    ) / len(requests) / 1000)
    strong_rps = sum(1 for request in requests if request.hard) / (data.WINDOW_MS / 1000)
    needed_batch = strong_rps / throughput_per_batch
    needed_wait = needed_batch * (1000 / strong_rps)

    slow = evaluate(reference.decide, 200.0)
    fast = evaluate(reference.decide, 300.0)
    check(
        slow["p95"] > TTFT_BUDGET_MS and fast["p95"] <= TTFT_BUDGET_MS,
        "the window cliff is not between 200ms and 300ms "
        f"(p95 {slow['p95']:.0f}ms and {fast['p95']:.0f}ms)",
    )

    base = evaluate(baseline.decide, 200.0)
    base_fails = sum(
        [
            base["quality"] < QUALITY_TARGET,
            base["p95"] > TTFT_BUDGET_MS,
            base["cost"] > COST_CAP_USD,
        ]
    )
    check(base_fails >= 2, f"the baseline only fails {base_fails} gate(s)")
    check(
        first["quality"] >= QUALITY_TARGET
        and first["p95"] <= TTFT_BUDGET_MS
        and first["cost"] <= COST_CAP_USD,
        "the reference does not clear all three gates",
    )

    if problems:
        print(f" {len(problems)} problem(s)")
        for problem in problems:
            print(f" - {problem}")
        return 1

    print(f" ok: {len(requests)} requests, {hard} hard ({hard / len(requests):.0%}), 40 rps")
    print(f" reference: quality {first['quality']:.1%}, p95 {first['p95']:.0f}ms, "
          f"${first['cost']:.6f}/request")
    print(f" baseline:  quality {base['quality']:.1%}, p95 {base['p95']:.0f}ms, "
          f"${base['cost']:.6f}/request, fails {base_fails} gates")
    print(
        f" capacity: one strong batch is {strong_service:.0f}ms, {throughput_per_batch:.2f} "
        f"batches/s over {SLOTS} slots; {strong_rps:.1f} rps needs a batch of "
        f"{needed_batch:.1f}, or a {needed_wait:.0f}ms window"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
