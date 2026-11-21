"""Field-level scoring.

Normalization matters more than people expect: a model that returns
"  ACME Corp. " and a date of "12 March 2026" is not wrong, it is unformatted.
Scoring without normalization teaches you to fight the wrong battle.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

SCORED_FIELDS = ("vendor", "invoice_date", "currency", "total")

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%d %B %Y",
    "%B %d, %Y",
    "%d %b %Y",
    "%b %d, %Y",
)


# -- normalization ----------------------------------------------------------


def norm_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"[^a-z0-9]", "", value.casefold())
    return cleaned or None


def norm_currency(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    m = re.search(r"\b([A-Za-z]{3})\b", value)
    return m.group(1).upper() if m else None


def norm_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def norm_money(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    from .model import parse_amount

    amount, _ = parse_amount(value)
    return amount


# -- comparison -------------------------------------------------------------


def matches(field_name: str, predicted: object, expected: object) -> bool:
    if field_name == "vendor":
        p, e = norm_text(predicted), norm_text(expected)
        return p is not None and p == e
    if field_name == "currency":
        p, e = norm_currency(predicted), norm_currency(expected)
        return p is not None and p == e
    if field_name == "invoice_date":
        p, e = norm_date(predicted), norm_date(expected)
        return p is not None and p == e
    if field_name == "total":
        p, e = norm_money(predicted), norm_money(expected)
        if p is None or e is None:
            return False
        return abs(p - e) <= 0.01
    raise ValueError(f"unknown field {field_name!r}")


def diagnose(field_name: str, predicted: object, expected: object) -> str:
    """A short human-readable cause, used to cluster failure modes."""
    if predicted is None:
        return "missing / null"
    if field_name == "total":
        p, e = norm_money(predicted), norm_money(expected)
        if p is None:
            return "unparseable amount"
        if e and abs(p - e) > 0.01:
            if abs(p - (e or 0)) and abs(p - 0) < 0.01:
                return "zero or empty total"
            return "wrong amount"
        return "wrong amount"
    if field_name == "invoice_date":
        if norm_date(predicted) is None:
            return "unparseable date"
        return "wrong date"
    if field_name == "vendor":
        return "wrong vendor"
    if field_name == "currency":
        if norm_currency(predicted) is None:
            return "missing currency"
        return "wrong currency"
    return "mismatch"


# -- scorecard --------------------------------------------------------------

BAR = "\u2500" * 62


@dataclass
class Scorecard:
    accuracy: float
    per_field: dict[str, float]
    cost_usd: float
    cost_per_doc: float
    p95_latency_ms: float
    calls: int
    calls_per_doc: float
    crashes: int
    n_docs: int
    failures: list[dict] = field(default_factory=list)
    modes: dict[str, int] = field(default_factory=dict)
    target_accuracy: float = 0.90
    max_cost_usd: float = 0.03
    min_calls_per_doc: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def meets_accuracy(self) -> bool:
        return self.accuracy >= self.target_accuracy

    @property
    def meets_cost(self) -> bool:
        return self.cost_usd <= self.max_cost_usd

    @property
    def uses_model(self) -> bool:
        """The point of the drill is the wrapper around the model, not a bypass."""
        return self.calls_per_doc >= self.min_calls_per_doc

    @property
    def passed(self) -> bool:
        return (
            self.meets_accuracy
            and self.meets_cost
            and self.crashes == 0
            and self.uses_model
        )

    def _check(self, ok: bool) -> str:
        return "PASS" if ok else "FAIL"

    def hints(self) -> list[str]:
        """Turn failure clusters into concrete next moves."""
        out: list[str] = []
        modes = self.modes

        def count(*needles: str) -> int:
            return sum(n for k, n in modes.items() if any(x in k for x in needles))

        if self.crashes:
            out.append(
                f"{self.crashes} crash(es). Your task raised instead of returning a dict — "
                "handle bad model output defensively."
            )
        if count("unparseable", "missing / null") > 2:
            out.append(
                "Model output is often not valid JSON. Repair it before you trust it: "
                "strip prose, close truncated objects, drop trailing commas."
            )
        if count("wrong amount") > 2:
            out.append(
                "Amounts are landing wrong. Check thousands separators and decimal "
                "commas, and cross-check total against subtotal + tax."
            )
        if count("wrong vendor") > 1:
            out.append(
                "Wrong vendor usually means you accepted an adjacent field "
                "(the bill-to party) as the supplier."
            )
        if count("wrong date", "unparseable date") > 1:
            out.append(
                "Date formats vary by locale. Normalize to ISO 8601 inside your task "
                "instead of hoping the grader is lenient."
            )
        if self.costs_growing():
            out.append(
                f"You are averaging {self.calls_per_doc:.1f} calls per document. "
                "Retry only on failures you can actually detect — blanket retries "
                "burn the budget."
            )
        return out

    def costs_growing(self) -> bool:
        return self.calls_per_doc > 2.2

    def render(self, title: str = "scorecard") -> str:
        lines = [BAR, f" {title}", BAR]
        lines.append(
            f" accuracy      {self.accuracy:6.1%}   target {self.target_accuracy:.0%}   "
            f"[{self._check(self.meets_accuracy)}]"
        )
        lines.append(
            f" cost          ${self.cost_usd:6.4f}   cap    ${self.max_cost_usd:6.4f}   "
            f"[{self._check(self.meets_cost)}]"
        )
        lines.append(f" crashes       {self.crashes:6d}   allowed 0   [{self._check(not self.crashes)}]")
        lines.append(
            f" model calls   {self.calls_per_doc:6.2f}/doc   "
            f"min {self.min_calls_per_doc:.1f}   [{self._check(self.uses_model)}]"
        )
        lines.append(f" calls         {self.calls:6d}")
        lines.append(f" latency p95   {self.p95_latency_ms:6.0f}ms")
        lines.append(BAR)
        lines.append(" metrics")
        for name, value in self.per_field.items():
            filled = int(round(value * 28))
            bar = "\u2588" * filled + "." * (28 - filled)
            lines.append(f"   {name:<18} {value:6.1%}  {bar}")
        lines.append(BAR)
        if self.modes:
            lines.append(" failure modes")
            for mode, n in sorted(self.modes.items(), key=lambda kv: -kv[1])[:5]:
                lines.append(f"   {n:3d}x  {mode}")
            lines.append(BAR)
        if self.notes:
            for note in self.notes:
                lines.append(f" note: {note}")
            lines.append(BAR)
        verdict = "TARGET MET" if self.passed else "keep going"
        lines.append(f" {verdict}")
        lines.append(BAR)
        return "\n".join(lines)


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))
    return ordered[idx]


def make_card(
    *,
    metrics: dict[str, float],
    model,
    n_items: int,
    target_accuracy: float,
    max_cost_usd: float,
    crashes: int = 0,
    modes: dict[str, int] | None = None,
    failures: list[dict] | None = None,
    notes: list[str] | None = None,
) -> Scorecard:
    """Build a scorecard for a drill whose metrics are not invoice fields.

    `accuracy` is the mean of the supplied metrics, so a drill with one number
    and a drill with four both read the same on the summary line.
    """
    accuracy = sum(metrics.values()) / len(metrics) if metrics else 0.0
    calls = model.n_calls
    return Scorecard(
        accuracy=accuracy,
        per_field=dict(metrics),
        cost_usd=model.cost_usd,
        cost_per_doc=model.cost_usd / n_items if n_items else 0.0,
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=calls,
        calls_per_doc=calls / n_items if n_items else 0.0,
        crashes=crashes,
        n_docs=n_items,
        failures=failures or [],
        modes=modes or {},
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        notes=notes or [],
    )


def score(
    results: list,
    model,
    *,
    target_accuracy: float,
    max_cost_usd: float,
) -> Scorecard:
    n = len(results)
    per_field: dict[str, float] = {}
    failures: list[dict] = []
    modes: dict[str, int] = {}
    crashes = 0

    for name in SCORED_FIELDS:
        hits = 0
        for res in results:
            if res.crash:
                continue
            expected = res.invoice.truth.get(name)
            predicted = res.prediction.get(name) if isinstance(res.prediction, dict) else None
            if matches(name, predicted, expected):
                hits += 1
            else:
                cause = diagnose(name, predicted, expected)
                modes[f"{name}: {cause}"] = modes.get(f"{name}: {cause}", 0) + 1
                failures.append(
                    {
                        "doc_id": res.invoice.doc_id,
                        "field": name,
                        "predicted": predicted,
                        "expected": expected,
                        "cause": cause,
                        "detail": " / ".join(res.invoice.raw.splitlines()[:2]),
                    }
                )
        per_field[name] = hits / n if n else 0.0

    for res in results:
        if res.crash:
            crashes += 1
            modes[f"crash: {res.crash.splitlines()[0][:60]}"] = (
                modes.get(f"crash: {res.crash.splitlines()[0][:60]}", 0) + 1
            )

    total_points = n * len(SCORED_FIELDS)
    accuracy = sum(per_field.values()) / len(SCORED_FIELDS) if per_field else 0.0

    return Scorecard(
        accuracy=accuracy,
        per_field=per_field,
        cost_usd=model.cost_usd,
        cost_per_doc=model.cost_usd / n if n else 0.0,
        p95_latency_ms=percentile(model.latencies, 0.95),
        calls=model.n_calls,
        calls_per_doc=model.n_calls / n if n else 0.0,
        crashes=crashes,
        n_docs=n,
        failures=failures,
        modes=modes,
        target_accuracy=target_accuracy,
        max_cost_usd=max_cost_usd,
        min_calls_per_doc=0.9,
    )
