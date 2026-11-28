#!/usr/bin/env python3
"""Recompute every decision with a second implementation.

    python3 drills/w23_finetune/check_labels.py

The answers in `data.TRUTH` were produced by the cost model, which makes them exactly the kind of
label that drifts silently when a constant changes. So this file does not import the reference
solution: it computes the same three costs from the constants, in a different order, and asserts
that each stored answer is the unique cheapest option that clears the bar.

1. 24 scenarios, 10 decided by cost, 8 by a constraint, 6 by the bar
2. every answer is one of prompting, rag, finetune, none
3. the recomputed answer equals the stored answer
4. among the options that are possible and above the bar, the cheapest is unique — no ties
5. a `cost` scenario has all three options possible and at least two above the bar
6. a `constraint` scenario has at least one option that is impossible
7. a `none` scenario has no possible option above the bar
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from drills.w23_finetune import data  # noqa: E402

TOLERANCE = 1e-9


def per_request(scenario, approach: str) -> float:
    """Dollars per request, before volume and before any fixed cost."""
    large = (scenario.prompt_tokens * data.LARGE_IN + scenario.output_tokens * data.LARGE_OUT) / 1e6
    if approach == "prompting":
        return large
    if approach == "rag":
        return (
            (scenario.prompt_tokens + scenario.retrieved_tokens) * data.LARGE_IN
            + scenario.output_tokens * data.LARGE_OUT
        ) / 1e6 + data.RETRIEVAL_FEE
    return (scenario.prompt_tokens * data.SMALL_IN + scenario.output_tokens * data.SMALL_OUT) / 1e6


def per_day(scenario, approach: str) -> float:
    total = scenario.requests * per_request(scenario, approach)
    if approach == "finetune":
        training = (
            scenario.examples
            * data.EPOCHS
            * scenario.example_tokens
            * data.TRAIN_PER_MTOKEN
            / 1e6
        )
        total += training / data.WINDOW_DAYS[scenario.facts]
    return total


def allowed(scenario, approach: str) -> bool:
    if approach == "prompting":
        return True
    if approach == "rag":
        return scenario.corpus
    return scenario.examples > 0 and scenario.facts != "weekly" and not scenario.citations


def q(scenario, approach: str) -> float:
    return scenario.quality[data.APPROACHES.index(approach)]


def decide(scenario) -> str:
    survivors = [a for a in data.APPROACHES if allowed(scenario, a) and q(scenario, a) >= scenario.bar]
    if not survivors:
        return "none"
    return min(survivors, key=lambda a: per_day(scenario, a))


def main() -> int:
    problems: list[str] = []
    ties: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    scenarios = data.build()
    check(len(scenarios) == 24, f"{len(scenarios)} scenarios, expected 24")
    check(
        len({scenario.id for scenario in scenarios}) == len(scenarios),
        "duplicate scenario ids",
    )

    kinds = Counter(scenario.kind for scenario in scenarios)
    check(
        dict(kinds) == {"cost": 10, "constraint": 8, "none": 6},
        f"kinds are {dict(kinds)}, expected 10/8/6",
    )

    for scenario in scenarios:
        truth = data.TRUTH.get(scenario.id)
        check(truth in data.ANSWERS, f"{scenario.id}: {truth!r} is not a valid answer")
        check(
            truth == decide(scenario),
            f"{scenario.id}: stored {truth}, recomputed {decide(scenario)}",
        )

        survivors = [
            approach
            for approach in data.APPROACHES
            if allowed(scenario, approach) and q(scenario, approach) >= scenario.bar
        ]
        if len(survivors) > 1:
            costs = sorted(per_day(scenario, approach) for approach in survivors)
            if costs[1] - costs[0] <= TOLERANCE:
                ties.append(
                    f"{scenario.id}: {survivors} tie at ${costs[0]:.6f}"
                )

        if scenario.kind == "cost":
            check(
                all(allowed(scenario, approach) for approach in data.APPROACHES),
                f"{scenario.id}: a cost scenario should have no impossible option",
            )
            check(
                len(survivors) >= 2,
                f"{scenario.id}: a cost scenario needs two options above the bar, "
                f"has {len(survivors)}",
            )
        if scenario.kind == "constraint":
            check(
                not all(allowed(scenario, approach) for approach in data.APPROACHES),
                f"{scenario.id}: a constraint scenario has no impossible option",
            )
        if truth == "rag":
            check(
                q(scenario, "prompting") < scenario.bar,
                f"{scenario.id}: retrieval wins, but prompting already clears the bar — "
                "retrieval is strictly more expensive per request, so it cannot win on cost",
            )
        if scenario.kind == "none":
            check(not survivors, f"{scenario.id}: a none scenario has {survivors} above the bar")

    if ties:
        problems.extend(f"tie: {tie}" for tie in ties)

    if problems:
        print(f" {len(problems)} problem(s)")
        for problem in problems:
            print(f" - {problem}")
        return 1

    print(f" ok: {len(scenarios)} scenarios, {kinds['cost']}/{kinds['constraint']}/{kinds['none']}")
    print(f" answers: {dict(Counter(data.TRUTH.values()))}")
    no_constraints = sum(
        1 for scenario in scenarios if decide(scenario) != decide_without_constraints(scenario)
    )
    no_bar = sum(1 for scenario in scenarios if decide(scenario) != decide_without_bar(scenario))
    print(f" dropping the constraint pass changes {no_constraints} of {len(scenarios)} answers")
    print(f" dropping the quality bar changes {no_bar} of {len(scenarios)} answers")
    return 0


def decide_without_constraints(scenario) -> str:
    survivors = [a for a in data.APPROACHES if q(scenario, a) >= scenario.bar]
    return min(survivors, key=lambda a: per_day(scenario, a)) if survivors else "none"


def decide_without_bar(scenario) -> str:
    survivors = [a for a in data.APPROACHES if allowed(scenario, a)]
    return min(survivors, key=lambda a: per_day(scenario, a))


if __name__ == "__main__":
    raise SystemExit(main())
