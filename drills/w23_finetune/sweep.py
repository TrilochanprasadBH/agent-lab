#!/usr/bin/env python3
"""Compare six ways to answer the architecture question.

    python3 drills/w23_finetune/sweep.py

  always rag           the industry default                               3 of 24
  always fine-tune     the other default                                  10 of 24
  cheapest, no filter  the spreadsheet answer, constraints ignored
  no quality bar       the cheapest thing that is possible
  most accurate        the best quality, cost ignored
  the three passes     possible, then good enough, then cheapest           the reference

Every number in `spec.md` comes from here. The middle rows are the point: each one is a real
decision procedure that omits one pass, and each one is wrong in a different group of scenarios.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentlab.drill import run_drill  # noqa: E402

from drills.w23_finetune import data  # noqa: E402
from drills.w23_finetune.drill import score  # noqa: E402
from solutions.w23_reference import choose as three_passes  # noqa: E402
from solutions.w23_reference import daily_cost, possible, quality  # noqa: E402


def always(approach: str):
    def strategy(scenario, model):
        return approach

    return strategy


def cheapest_ignoring_constraints(scenario, model):
    return min(data.APPROACHES, key=lambda approach: daily_cost(scenario, approach))


def cheapest_ignoring_the_bar(scenario, model):
    options = [approach for approach in data.APPROACHES if possible(scenario, approach)]
    return min(options, key=lambda approach: daily_cost(scenario, approach))


def most_accurate(scenario, model):
    options = [
        approach
        for approach in data.APPROACHES
        if possible(scenario, approach) and quality(scenario, approach) >= scenario.bar
    ]
    if not options:
        return "none"
    return max(options, key=lambda approach: quality(scenario, approach))


STRATEGIES = (
    ("always rag", always("rag")),
    ("always fine-tune", always("finetune")),
    ("cheapest, no filter", cheapest_ignoring_constraints),
    ("no quality bar", cheapest_ignoring_the_bar),
    ("most accurate", most_accurate),
    ("the three passes", three_passes),
)


def evaluate(strategy):
    scenarios = data.build()
    model = data.model()
    results = run_drill(scenarios, strategy, model)
    return score(results, model, 0.90, 0.0)


def main() -> int:
    scenarios = data.build()
    print()
    print(
        f" {len(scenarios)} scenarios: "
        f"{sum(1 for s in scenarios if s.kind == 'cost')} decided by cost, "
        f"{sum(1 for s in scenarios if s.kind == 'constraint')} by a constraint, "
        f"{sum(1 for s in scenarios if s.kind == 'none')} by the bar"
    )
    print()
    print(f" {'strategy':<24}{'overall':>8}{'cost':>7}{'constr':>8}{'none':>7}  what it misses")
    notes = {
        "always rag": "everything that is not a retrieval problem",
        "always fine-tune": "every low-volume, citation and changing-facts case",
        "cheapest, no filter": "the option it picked cannot be built",
        "no quality bar": "the cheapest option is below the bar",
        "most accurate": "the second-decimal cost of the best answer",
        "the three passes": "",
    }
    for name, strategy in STRATEGIES:
        card = evaluate(strategy)
        print(
            f" {name:<24}{card.accuracy:>8.1%}"
            f"{card.per_field['decided by cost']:>7.0%}"
            f"{card.per_field['by constraint']:>8.0%}"
            f"{card.per_field['bar not met']:>7.0%}  {notes[name]}"
        )
    print()

    print(" daily cost per option, for the scenarios where cost decides")
    print()
    print(f" {'scenario':<8}{'requests':>9}{'prompt':>9}{'rag':>10}{'fine-tune':>11}  chosen")
    for scenario in scenarios:
        if scenario.kind != "cost":
            continue
        print(
            f" {scenario.id:<8}{scenario.requests:>9}"
            f"{daily_cost(scenario, 'prompting'):>9.2f}"
            f"{daily_cost(scenario, 'rag'):>10.2f}"
            f"{daily_cost(scenario, 'finetune'):>11.2f}"
            f"  {data.TRUTH[scenario.id]}"
        )
    print()
    print(" dollars per day. Retrieval is never the cheapest: it pays for the retrieved tokens")
    print(" and a fee on every request, so it can only win when prompting misses the bar.")
    print(" Fine-tuning wins where the volume amortises the training and loses at the bottom")
    print(" of the range, where the fixed cost is the whole bill.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
