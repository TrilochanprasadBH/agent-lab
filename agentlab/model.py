"""A deterministic stand-in for a hosted language model.

It is deliberately *not* a good extractor. It finds the invoice that appears in
the prompt, reads it with cheap regular expressions, and then corrupts its own
answer at a configurable rate.

Nothing in this file can see the ground truth. Its accuracy is whatever its
heuristics and its corruption produce — which is the whole point of the drill:
you cannot fix the model, you can only fix the system around it.

Determinism
-----------
Every call hashes (seed, prompt, attempt number for that exact prompt). Two runs
of the same solution score identically. Retrying with the *same* prompt yields a
different answer (real models do this too); retrying with a *changed* prompt
starts a fresh attempt sequence.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

PRICE_IN_PER_MTOK = 0.50
PRICE_OUT_PER_MTOK = 1.50

SYMBOLS = {"$": "USD", "\u20ac": "EUR", "\u00a3": "GBP", "\u20b9": "INR"}


@dataclass
class Response:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float
    finish_reason: str = "stop"

    def __str__(self) -> str:
        return self.text


def _unit(*parts: object) -> float:
    """A stable pseudo-random float in [0, 1) derived from the arguments."""
    h = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(h[:13], 16) / float(16**13)


# --------------------------------------------------------------------------
# Amount and date parsing — the heuristics the fake model itself uses.
# These are decent but not perfect, which is what makes the dataset interesting.
# --------------------------------------------------------------------------


def parse_amount(text: str) -> tuple[float | None, str | None]:
    """Pull a number and an ISO currency code out of a messy amount string."""
    if not text:
        return None, None

    currency = None
    m = re.search(r"\b([A-Z]{3})\b", text)
    if m:
        currency = m.group(1)
    for sym, code in SYMBOLS.items():
        if sym in text:
            currency = currency or code

    num = re.sub(r"[^0-9.,\-]", "", text)
    if not num or not re.search(r"\d", num):
        return None, currency

    if "," in num and "." in num:
        if num.rfind(",") > num.rfind("."):
            num = num.replace(".", "").replace(",", ".")
        else:
            num = num.replace(",", "")
    elif "," in num:
        # "1,350" is thousands; "12,50" is a decimal comma
        if re.search(r",\d{2}$", num) and num.count(",") == 1:
            num = num.replace(",", ".")
        else:
            num = num.replace(",", "")

    try:
        return float(num), currency
    except ValueError:
        return None, currency


def _field(doc: str, label: str) -> str | None:
    m = re.search(rf"^\s*(?:{label})\s*:\s*(.+)$", doc, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else None


def heuristic_extract(doc: str) -> dict[str, object]:
    """What the fake model 'understands' before it starts making mistakes."""
    total_raw = _field(doc, "Total Due|Amount Due|Total")
    sub_raw = _field(doc, "Subtotal|Sub-total|Net")
    tax_raw = _field(doc, "Tax(?: \\([^)]*\\))?|VAT(?: \\([^)]*\\))?")
    date_raw = _field(doc, "Invoice Date|Issued|Date")

    total, cur = parse_amount(total_raw or "")
    subtotal, _ = parse_amount(sub_raw or "")
    tax, _ = parse_amount(tax_raw or "")

    return {
        "vendor": _field(doc, "Supplier|Vendor"),
        "invoice_date": date_raw,
        "currency": cur,
        "subtotal": subtotal,
        "tax": tax,
        "total": total,
        "_bill_to": _field(doc, "Bill To|Customer|Client"),
    }


# --------------------------------------------------------------------------
# Corruption. Each entry turns a correct-ish extraction into a plausible error.
# --------------------------------------------------------------------------

CORRUPTIONS: tuple[tuple[str, float], ...] = (
    ("verbose_prefix", 0.12),
    ("string_numbers", 0.06),
    ("billed_to", 0.12),
    ("subtotal_as_total", 0.10),
    ("trailing_comma", 0.10),
    ("truncate", 0.12),
    ("refusal", 0.06),
)

REFUSALS = (
    "I'm sorry, but I can't help with extracting data from that document.",
    "I'm not able to process invoices. Please try a different request.",
)


class SimModel:
    """A flaky, deterministic, offline model with token accounting."""

    def __init__(self, corpus: list[str], *, seed: int = 7) -> None:
        self.corpus = list(corpus)
        self.seed = seed
        self.calls: list[dict[str, object]] = []
        self._seen: dict[str, int] = {}
        self._cost = 0.0
        self._latencies: list[float] = []

    # -- bookkeeping ------------------------------------------------------

    def reset(self) -> None:
        self.calls.clear()
        self._seen.clear()
        self._cost = 0.0
        self._latencies.clear()

    @property
    def cost_usd(self) -> float:
        return self._cost

    @property
    def latencies(self) -> list[float]:
        return list(self._latencies)

    @property
    def n_calls(self) -> int:
        return len(self.calls)

    # -- the only public API your task should use -------------------------

    def complete(self, prompt: str, system: str | None = None) -> Response:
        text, finish = self._respond(prompt, system)

        tokens_in = max(1, (len(prompt) + len(system or "")) // 4)
        tokens_out = max(1, len(text) // 4)
        cost = (
            tokens_in * PRICE_IN_PER_MTOK + tokens_out * PRICE_OUT_PER_MTOK
        ) / 1_000_000

        latency = 140.0 + 900.0 * _unit(self.seed, prompt[-200:], "lat")
        latency = round(latency, 1)

        self._cost += cost
        self._latencies.append(latency)
        self.calls.append(
            {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(cost, 8),
                "latency_ms": latency,
                "finish_reason": finish,
                "prompt_tail": prompt[-160:],
                "output": text,
            }
        )

        return Response(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency,
            cost_usd=cost,
            finish_reason=finish,
        )

    # -- internals --------------------------------------------------------

    def _locate(self, prompt: str) -> str | None:
        best = None
        for doc in self.corpus:
            if doc in prompt and (best is None or len(doc) > len(best)):
                best = doc
        return best

    def _respond(self, prompt: str, system: str | None) -> tuple[str, str]:
        key = hashlib.sha256((system or "").encode() + b"\x00" + prompt.encode()).hexdigest()
        attempt = self._seen.get(key, 0)
        self._seen[key] = attempt + 1

        doc = self._locate(prompt)
        if doc is None:
            return (
                "I couldn't find an invoice in that message. "
                "Please include the document text.",
                "stop",
            )

        rolls = [
            _unit(self.seed, key[:16], attempt, name) for name, _ in CORRUPTIONS
        ]
        fired = {
            name for (name, prob), roll in zip(CORRUPTIONS, rolls) if roll < prob
        }

        if "refusal" in fired:
            pick = int(_unit(self.seed, attempt, "r") * len(REFUSALS))
            return REFUSALS[pick], "stop"

        data = heuristic_extract(doc)

        if "billed_to" in fired and data.get("_bill_to"):
            data["vendor"] = data["_bill_to"]
        if "subtotal_as_total" in fired and data.get("subtotal") is not None:
            data["total"] = data["subtotal"]

        payload = {k: v for k, v in data.items() if not k.startswith("_")}

        if "string_numbers" in fired:
            payload = {
                k: (f"{v:,.2f}" if isinstance(v, float) else v)
                for k, v in payload.items()
            }

        text = json.dumps(payload, indent=2)

        if "trailing_comma" in fired:
            text = re.sub(r"\n(\s*)\}", r",\n\1}", text, count=1)

        if "truncate" in fired:
            cut = 0.45 + 0.4 * _unit(self.seed, attempt, "cut")
            text = text[: max(20, int(len(text) * cut))]

        if "verbose_prefix" in fired:
            text = "Sure! Here's the data I pulled out:\n\n```json\n" + text + "\n```"

        return text, ("length" if "truncate" in fired else "stop")
