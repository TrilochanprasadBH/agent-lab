"""Drill 01 — structured extraction from messy invoices.

You edit `task.py`. Everyone else in the lab follows the same shape:

    corpus()        the seeded items, each carrying its ground truth
    build_model()   the world's model (simulated, scripted, or real)
    score()         how this drill's numbers are computed
"""

from __future__ import annotations

from agentlab.evals import score as field_score
from agentlab.model import SimModel

from .data import generate

NAME = "w01 \u00b7 schema repair & verification"
PREMISE = "An unreliable extractor, a messy invoice corpus, one honest number."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 0.012
SUPPORTS_REAL = True
TASK_NAME = "extract"


def corpus() -> list:
    return generate()


def build_model(seed: int = 7):
    items = corpus()
    return SimModel([inv.raw for inv in items], seed=seed)


def score(results, model, target_accuracy: float, max_cost_usd: float):
    return field_score(
        results,
        model,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
    )
