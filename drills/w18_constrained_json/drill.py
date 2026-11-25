"""Drill 18 — always-valid JSON."""

from __future__ import annotations

import re

from agentlab.evals import Scorecard, percentile

from . import data

NAME = "w18 - valid JSON, and the difference between valid and right"
PREMISE = "Extract three fields into a schema, knowing that a perfect object can still be wrong."
TARGET_ACCURACY = 0.82
MAX_COST_USD = 0.020
SUPPORTS_REAL = False
TASK_NAME = "extract"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def corpus() -> list:
    return data.build()


def build_model(seed: int = 2027):
    return data.model(data.build())


def validate(payload: dict) -> list[str]:
    """The schema, as a list of reasons it does not hold. Empty means valid."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return ["not an object"]

    for key in ("vendor", "invoice_date", "total"):
        if key not in payload:
            problems.append(f"missing {key}")

    vendor = payload.get("vendor")
    if not isinstance(vendor, str) or not vendor.strip():
        problems.append("vendor is not a non-empty string")

    date = payload.get("invoice_date")
    if not isinstance(date, str) or not DATE.match(date):
        problems.append("invoice_date is not YYYY-MM-DD")

    total = payload.get("total")
    if isinstance(total, bool) or not isinstance(total, (int, float)):
        problems.append("total is not a number")

    return problems


def correct(payload: dict, truth: dict) -> bool:
    return (
        payload.get("vendor") == truth["vendor"]
        and payload.get("invoice_date") == truth["invoice_date"]
        and isinstance(payload.get("total"), (int, float))
        and not isinstance(payload.get("total"), bool)
        and abs(float(payload["total"]) - truth["total"]) < 0.01
    )


def score(results, model, target_accuracy: float, max_cost_usd: float):
    valid = correct_count = invisible = 0
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        case = result.invoice
        payload = result.prediction if isinstance(result.prediction, dict) else {}
        problems = validate(payload)
        if problems:
            modes[problems[0]] = modes.get(problems[0], 0) + 1
            failures.append(
                {"doc_id": case.id, "cause": problems[0], "predicted": payload}
            )
            continue

        valid += 1
        if correct(payload, case.truth):
            correct_count += 1
        else:
            invisible += 1
            modes["valid but names the wrong party"] = (
                modes.get("valid but names the wrong party", 0) + 1
            )
            failures.append(
                {
                    "doc_id": case.id,
                    "cause": "valid but wrong",
                    "predicted": payload.get("vendor"),
                    "expected": case.truth["vendor"],
                }
            )

    n = len(results) or 1
    validity = valid / n
    accuracy = correct_count / n

    # Validity is a gate, not the score: an object that parses and carries the wrong vendor is
    # the failure nobody notices, so the number that counts is valid *and* correct.
    gate = 0.99
    scored = accuracy if validity >= gate else 0.0

    notes = [
        f"valid {valid}/{len(results)} ({validity:.1%}), valid and correct {correct_count}/{len(results)} ({accuracy:.1%})",
        f"{invisible} of {len(results)} objects were valid and named the wrong party",
        f"{model.n_calls} calls, {model.n_calls / n:.2f} per case",
    ]
    if validity < gate:
        notes.append(f"scored zero: validity below {gate:.0%}")

    return Scorecard(
        accuracy=scored,
        per_field={
            "valid": validity,
            "correct": accuracy,
            "invisible errors": invisible / n,
        },
        cost_usd=model.cost_usd,
        cost_per_doc=model.cost_usd / n,
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=model.n_calls,
        calls_per_doc=model.n_calls / n,
        crashes=sum(1 for result in results if result.crash),
        n_docs=len(results),
        failures=failures,
        modes=modes,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        min_calls_per_doc=0.9,
        notes=notes,
        hints_override=[
            "The free reply is broken in ways you can see: truncated, trailing comma, prose, a "
            "number as a string, a long date, a missing field. A parser handles some of them.",
            "The model takes a schema argument. Passing it makes the sampler emit a valid object, "
            "which is what a structured-output API does. It costs twice as much per call.",
            "Retrying is cheaper than the schema and cannot get you past about 94% validity, and "
            "the target is 99%.",
            "Read the 'valid but wrong' failures. No schema, parser or retry will fix those, and "
            "the brief says what would.",
        ],
    )
