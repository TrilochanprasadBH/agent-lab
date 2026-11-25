"""Drill 17 — redacting personal data."""

from __future__ import annotations

from agentlab.evals import Scorecard, percentile

from . import data

NAME = "w17 - redact personal data without shredding the message"
PREMISE = "Find every personal data span in forty support messages, and nothing else."
TARGET_ACCURACY = 0.93
MAX_COST_USD = 0.10
SUPPORTS_REAL = False
TASK_NAME = "redact"
PRECISION_FLOOR = 0.90


def corpus() -> list:
    return data.build()


def build_model(seed: int = 2027):
    return data.model(data.build())


def score(results, model, target_accuracy: float, max_cost_usd: float):
    gold_total = recalled = predicted = precise = invalid = 0
    leaks_by_category: dict[str, int] = {}
    modes: dict[str, int] = {}
    failures: list[dict] = []

    for result in results:
        message = result.invoice
        payload = result.prediction if isinstance(result.prediction, dict) else {}
        rows = payload.get("spans") or []

        predictions: list[tuple[int, int, str]] = []
        for row in rows:
            try:
                start, end, category = int(row[0]), int(row[1]), str(row[2])
            except (TypeError, ValueError, IndexError):
                invalid += 1
                modes["malformed span triples"] = modes.get("malformed span triples", 0) + 1
                continue
            if not 0 <= start < end <= len(message.text):
                invalid += 1
                modes["span outside the text"] = modes.get("span outside the text", 0) + 1
                continue
            if category not in data.CATEGORIES:
                invalid += 1
                modes["unknown category"] = modes.get("unknown category", 0) + 1
                continue
            predictions.append((start, end, category))

        gold_total += len(message.spans)
        predicted += len(predictions)

        # A gold span is protected when every character of it is covered, by one prediction or
        # by several. Two names redacted separately is a success, not a leak.
        covered = [False] * len(message.text)
        for start, end, _ in predictions:
            for position in range(start, end):
                covered[position] = True

        for span in message.spans:
            if all(covered[span.start : span.end]):
                recalled += 1
            else:
                leaks_by_category[span.category] = leaks_by_category.get(span.category, 0) + 1
                failures.append(
                    {
                        "doc_id": message.id,
                        "cause": f"leaked {span.category}",
                        "detail": message.text[span.start : span.end],
                    }
                )

        for start, end, _ in predictions:
            if any(start < span.end and end > span.start for span in message.spans):
                precise += 1
            else:
                modes["redacted something that was not personal data"] = (
                    modes.get("redacted something that was not personal data", 0) + 1
                )
                failures.append(
                    {
                        "doc_id": message.id,
                        "cause": "over-redaction",
                        "detail": message.text[start:end],
                    }
                )

    recall = recalled / gold_total if gold_total else 0.0
    precision = precise / predicted if predicted else 0.0
    over_redaction = 1 - precision
    within_floor = precision >= PRECISION_FLOOR and invalid == 0

    # A leak is the failure this drill exists to prevent, so recall is the score. Over-redaction
    # is a hard gate: shredding the message protects the data and destroys the answer.
    accuracy = recall if within_floor else 0.0

    notes = [
        f"recall {recall:.1%} ({recalled}/{gold_total} spans), precision {precision:.1%} "
        f"({precise}/{predicted})",
        f"over-redaction {over_redaction:.1%} (floor {1 - PRECISION_FLOOR:.0%})",
    ]
    if leaks_by_category:
        worst = sorted(leaks_by_category.items(), key=lambda item: -item[1])
        notes.append("leaks by category: " + ", ".join(f"{name} {count}" for name, count in worst))
    if not within_floor:
        notes.append("scored zero: precision floor missed or malformed spans")

    return Scorecard(
        accuracy=accuracy,
        per_field={
            "recall": recall,
            "precision": precision,
            "leaks": (gold_total - recalled) / gold_total if gold_total else 0.0,
        },
        cost_usd=model.cost_usd,
        cost_per_doc=model.cost_usd / len(results) if results else 0.0,
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=model.n_calls,
        calls_per_doc=model.n_calls / len(results) if results else 0.0,
        crashes=sum(1 for result in results if result.crash),
        n_docs=len(results),
        failures=failures,
        modes=modes,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        min_calls_per_doc=0.9,
        notes=notes,
        hints_override=[
            "Structured identifiers are a pattern problem: email, phone, IBAN and national id "
            "have shapes a regex matches precisely.",
            "A card number is a sixteen-digit run that passes Luhn. Counting digits redacts order "
            "numbers, which is how the baseline's precision collapses.",
            "The tagger finds addresses and most names. Merge its spans with your own, reject any "
            "that overlap, and keep the model out of the structured categories.",
            "Read the leak note: it names the category you are missing, and that is the next "
            "rule to write.",
        ],
    )
