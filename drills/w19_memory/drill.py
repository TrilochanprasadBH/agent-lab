"""Drill 19 — memory under a fixed budget."""

from __future__ import annotations

import re

from agentlab.evals import Scorecard, percentile

from . import data
from .data import BUDGET_TOKENS

NAME = "w19 - keeping the facts that matter when the context does not fit"
PREMISE = "Answer twelve probes about a 600-token conversation from 160 tokens of memory."
TARGET_ACCURACY = 0.85
MAX_COST_USD = 0.020
SUPPORTS_REAL = False
TASK_NAME = "remember"

CATEGORIES = ("early", "constraint", "corrected", "late", "unstructured")
ABSTENTIONS = ("i don't know", "i do not know", "unknown", "", "n/a")


def corpus() -> list:
    return data.build()


def build_model(seed: int = 2027):
    conversations = data.build()
    return data.model(conversations)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[,£$]", "", text.casefold())).strip()


def _contains(haystack: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(_norm(phrase)) + r"(?!\w)", haystack) is not None


def retained(probe, answer: str) -> bool:
    haystack = _norm(answer)
    return any(_contains(haystack, phrase) for phrase in probe.accept)


def abstained(answer: str) -> bool:
    text = _norm(answer).rstrip(".")
    return any(text.startswith(prefix) for prefix in ABSTENTIONS if prefix) or text == ""


def score(results, model, target_accuracy: float, max_cost_usd: float):
    total = correct = wrong = abstain = 0
    per_category = {category: [0, 0] for category in CATEGORIES}
    modes: dict[str, int] = {}
    failures: list[dict] = []
    crashes = 0

    def bump(key: str) -> None:
        modes[key] = modes.get(key, 0) + 1

    for result in results:
        conversation = result.invoice
        answers = result.prediction if isinstance(result.prediction, list) else []
        if result.crash:
            crashes += 1
            bump(f"crashed: {result.crash.split(':')[0]}")

        for index, probe in enumerate(conversation.probes):
            total += 1
            per_category[probe.category][1] += 1
            answer = answers[index] if index < len(answers) else ""

            if retained(probe, answer):
                correct += 1
                per_category[probe.category][0] += 1
            elif abstained(answer):
                abstain += 1
                bump("said it did not know")
            else:
                wrong += 1
                bump("answered with a wrong value")
                failures.append(
                    {
                        "doc_id": probe.id,
                        "cause": "wrong value",
                        "detail": probe.question,
                        "expected": probe.accept[0],
                        "predicted": answer,
                    }
                )

    per_field = {"retained": correct / total if total else 0.0}
    for category in CATEGORIES:
        hit, seen = per_category[category]
        per_field[category] = hit / seen if seen else 0.0
    per_field["wrong answers"] = wrong / total if total else 0.0
    per_field["abstained"] = abstain / total if total else 0.0

    notes = [
        f"budget {BUDGET_TOKENS} tokens; largest memory sent {model.max_memory_tokens}",
        f"{correct}/{total} probes retained, {wrong} answered wrong, {abstain} abstained",
        f"{model.n_calls} calls, {model.n_calls / len(results):.1f} per conversation",
    ]
    if wrong:
        notes.append(
            "every wrong answer is a confident value the customer never gave, not a refusal"
        )

    return Scorecard(
        accuracy=correct / total if total else 0.0,
        per_field=per_field,
        cost_usd=model.cost_usd,
        cost_per_doc=model.cost_usd / max(1, len(results)),
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=model.n_calls,
        calls_per_doc=model.n_calls / max(1, len(results)),
        crashes=crashes,
        n_docs=len(results),
        failures=failures,
        modes=modes,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        min_calls_per_doc=13.0,
        notes=notes,
        hints_override=[
            "You are dropping facts, not summarising them badly. Group the probes by "
            "category: truncation is perfect on `late` and zero on everything else.",
            "The postcode and the date are corrected mid-conversation. Read the sentence that "
            "does the correcting: it names the new value and then the old one.",
            "A fact ledger costs about 45 tokens for all twelve facts. Label each value with "
            "what it is; the model needs to recognise it, not to reason about it.",
            "Compression is not the goal. Twelve labelled values fit in a third of the budget, "
            "so there is no reason to summarise prose into the space the facts need.",
        ],
    )
