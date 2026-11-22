"""Drill 13 — eval set design."""

from __future__ import annotations

from collections import Counter

from agentlab.evals import make_card
from agentlab.providers import ScriptedModel

from .data import PER_CELL, POOL, cells as all_cells, corpus as pool

NAME = "w13 \u00b7 designing an eval set"
PREMISE = "A sample that misses a category cannot tell you that the category broke."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 1.0
SUPPORTS_REAL = False
TASK_NAME = "select"


def corpus() -> list:
    return pool()


def build_model(seed: int = 7):
    return ScriptedModel({})


def score(results, model, target_accuracy: float, max_cost_usd: float):
    by_id = {item.doc_id: item for item in POOL}
    cells = all_cells()

    selections: list[list] = []
    crashes = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        if result.crash:
            crashes += 1
            modes["crash"] = modes.get("crash", 0) + 1
            selections.append([])
            continue
        picked = result.prediction if isinstance(result.prediction, list) else []
        selections.append([pid for pid in picked if pid in by_id])

    covered = Counter()
    dup_penalty = 0
    total = 0

    for picked in selections:
        total += len(picked)
        seen_sources = Counter()
        for pid in picked:
            item = by_id[pid]
            seen_sources[item.source] += 1
            covered[(item.tag, item.difficulty)] += 1
        dup_penalty += sum(count - 1 for count in seen_sources.values() if count > 1)

    cell_coverage = sum(min(covered[c] // PER_CELL, 1) for c in cells) / len(cells)
    no_dupes = 1.0 - (dup_penalty / total if total else 1.0)

    missing = [c for c in cells if covered[c] < PER_CELL]
    for cell in missing[:6]:
        failures.append(
            {
                "doc_id": f"{cell[0]}/{cell[1]}",
                "cause": "cell underrepresented",
                "detail": f"{covered[cell]} of {PER_CELL} required items",
                "expected": PER_CELL,
                "predicted": covered[cell],
            }
        )

    metrics = {"cell coverage": cell_coverage, "no duplicate sources": no_dupes}
    return make_card(
        metrics=metrics,
        model=model,
        n_items=len(selections),
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        crashes=crashes,
        modes=modes,
        failures=failures,
        notes=[f"{dup_penalty} duplicate-source slot(s) wasted"],
    )
