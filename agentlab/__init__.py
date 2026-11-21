"""agentlab — a small harness for the Agent Lab drills.

Three pieces:

    model   a deterministic stand-in for a hosted LLM (flawed on purpose)
    evals   field-level scoring with normalization
    drill   runs your task over a seeded corpus and builds a scorecard
"""

from .model import Response, SimModel
from .evals import Scorecard, make_card, score
from .drill import Result, run_drill
from .providers import OpenRouterModel, ProviderError, ScriptedModel, make_provider
from .tools import Param, Tool, ToolRegistry

__all__ = [
    "Response",
    "SimModel",
    "Scorecard",
    "make_card",
    "score",
    "Result",
    "run_drill",
    "OpenRouterModel",
    "ProviderError",
    "ScriptedModel",
    "make_provider",
    "Param",
    "Tool",
    "ToolRegistry",
]
