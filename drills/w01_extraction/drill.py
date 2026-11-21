"""Drill configuration. Read by run.py — you should not need to edit this."""

from __future__ import annotations

from agentlab.model import SimModel

from .data import generate
from .task import extract

NAME = "w01 \u00b7 schema repair & verification"
PREMISE = "An unreliable extractor, a messy invoice corpus, one honest number."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 0.012


def corpus() -> list:
    """The seeded documents for this drill."""
    return generate()


def build(seed: int = 7, provider=None) -> tuple[list, object]:
    """Return (corpus, model).

    `provider` may be any object with the model contract; when omitted the
    simulated model is used.
    """
    corpus = generate()
    if provider is None:
        provider = SimModel([inv.raw for inv in corpus], seed=seed)
    return corpus, provider


def get_task():
    return extract
