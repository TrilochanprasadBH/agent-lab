"""agentlab — a small harness for the Agent Lab drills.

Three pieces:

    model   a deterministic stand-in for a hosted LLM (flawed on purpose)
    evals   field-level scoring with normalization
    drill   runs your task over a seeded corpus and builds a scorecard
"""

from .model import Response, SimModel
from .evals import Scorecard, score
from .drill import Result, run_drill

__all__ = ["Response", "SimModel", "Scorecard", "score", "Result", "run_drill"]
