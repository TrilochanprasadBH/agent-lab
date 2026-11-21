"""Drill configuration. Read by run.py — you should not need to edit this."""

from __future__ import annotations

from agentlab.model import SimModel

from .data import generate
from .task import extract

NAME = "w01 \u00b7 schema repair & verification"
PREMISE = "An unreliable extractor, a messy invoice corpus, one honest number."
TARGET_ACCURACY = 0.90
MAX_COST_USD = 0.012


def build(seed: int = 7) -> tuple[list, SimModel]:
    corpus = generate()
    model = SimModel([inv.raw for inv in corpus], seed=seed)
    return corpus, model


def get_task():
    return extract
