#!/usr/bin/env python3
"""Compare four ways of reading the same traces.

    python3 drills/w20_debug/sweep.py

  blame the model    the answer is wrong, so the model is wrong            1 rule
  score heuristic    low retrieval score -> retrieval, full prompt -> packing
  cheap checks       index, then ranking, then answer                      the natural order
  ladder             index, chunk, ranking, prompt, answer                 the reference

Every number in `spec.md` comes from here. The ladder row is the shipped reference solution, so
this table and `run.py --task solutions/w20_reference.py` cannot disagree.

The lesson is in the gap between `cheap checks` and `ladder`. Both know all seven stages; they
differ only in the order they ask the questions. Knowing more is not what fixes this — asking in
the order the pipeline runs is.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentlab.drill import run_drill  # noqa: E402

from drills.w20_debug import data  # noqa: E402
from drills.w20_debug.data import FIXES, HYBRID, contains  # noqa: E402
from drills.w20_debug.drill import score  # noqa: E402
from solutions.w20_reference import diagnose as ladder  # noqa: E402


def _fix(stage: str) -> str:
    return FIXES[stage]


def blame_the_model(case, model):
    return {"stage": "generation", "fix": "ground"}


def score_heuristic(case, model):
    if case.ranking[0][1] < 0.55:
        return {"stage": "retrieval", "fix": HYBRID}
    if case.prompt_tokens >= case.budget:
        return {"stage": "packing", "fix": "repack"}
    if "could not find" in case.answer:
        return {"stage": "retrieval", "fix": HYBRID}
    return {"stage": "generation", "fix": "ground"}


def cheap_checks(case, model):
    """Every check the ladder makes, in the order most people write them."""
    joined = "".join(chunk.text for chunk in case.index)
    if not contains(joined, case.gold):
        return {"stage": "ingestion", "fix": "reingest"}
    if case.gold_chunk is None:
        return {"stage": "ingestion", "fix": "reingest"}
    if case.gold_chunk not in case.retrieved:
        return {"stage": "retrieval", "fix": HYBRID}
    if not contains(case.answer, case.gold):
        return {"stage": "generation", "fix": "ground"}
    return {"stage": "packing", "fix": "repack"}


STRATEGIES = (
    ("blame the model", blame_the_model),
    ("score heuristic", score_heuristic),
    ("cheap checks", cheap_checks),
    ("ladder", ladder),
)


def evaluate(strategy):
    cases = data.build()
    model = data.model()
    results = run_drill(cases, strategy, model)
    return score(results, model, 0.90, 0.0)


def main() -> int:
    cases = data.build()
    print()
    print(f" {len(cases)} cases, {len(data.STAGES)} stages, {len(cases) // len(data.STAGES)} of each")
    print()
    print(f" {'strategy':<18}{'joint':>7}{'stage':>7}{'fix':>7}   {'what it misses':<34}")
    notes = {
        "blame the model": "everything that is not the last stage",
        "score heuristic": "confidence is not a diagnosis",
        "cheap checks": "chunking, query, packing, stale",
        "ladder": "nothing",
    }
    for name, strategy in STRATEGIES:
        card = evaluate(strategy)
        print(
            f" {name:<18}{card.accuracy:>7.1%}"
            f"{card.per_field['stage right']:>7.1%}"
            f"{card.per_field['fix right']:>7.1%}"
            f"   {notes[name]:<34}"
        )
    print()
    print(" joint = stage and fix both right; stage/fix are the marginals.")
    print()

    corpus_values = {doc.values[param] for doc in data.DOCS for param in data.PARAMS}
    buckets = {
        "answer admits it could not find the document": 0,
        "answer states a real value from the wrong chunk": 0,
        "answer states an older value from a superseded chunk": 0,
        "answer invents a number that appears nowhere": 0,
    }
    for case in cases:
        if "could not find" in case.answer:
            buckets["answer admits it could not find the document"] += 1
        elif any(contains(case.answer, value) for value in corpus_values if value != case.gold):
            buckets["answer states a real value from the wrong chunk"] += 1
        elif any(
            chunk.superseded and chunk.value and contains(case.answer, chunk.value)
            for chunk in case.index
        ):
            buckets["answer states an older value from a superseded chunk"] += 1
        else:
            buckets["answer invents a number that appears nowhere"] += 1

    print(" what the symptom looks like, across all cases")
    for label, count in buckets.items():
        print(f"   {label:<56}{count:>3}")
    confident = sum(1 for case in cases if case.ranking[0][1] >= 0.85)
    print(f"   {'top retrieval score at or above 0.85':<56}{confident:>3}")
    print()
    print(" the symptom is identical in every case and the score is confident in every case.")
    print(" neither tells you where to look.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
