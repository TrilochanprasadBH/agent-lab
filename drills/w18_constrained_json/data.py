"""Drill 18 — always-valid JSON, and the difference between valid and right.

The model extracts three fields from an invoice email: the vendor, the invoice date, the total.
It produces JSON that is often broken in one of two ways.

**Broken in a way you can see.** Truncated, a trailing comma, a sentence in front of the object,
a number as `"1,234.50"`, a date as `12 March 2026` when the schema says `YYYY-MM-DD`, a missing
field. Every one of these is detectable, and every one is fixable by a parser that pays attention
or a retry that gets a fresh sample.

**Broken in a way you cannot see.** The invoice has a seller and a buyer. Sometimes the model
returns the buyer. The JSON is perfect. The total is right, the date is right, the vendor is the
customer, and nothing about the text says so. No parser, no schema, and no retry count will catch
it.

That is the drill. Schema-constrained decoding gets you to 100% valid; it does not move the
wrong-vendor rate by a single point. The only thing that catches a wrong party is a check against
something other than the model.

    free text      70% of replies carry a visible defect, 13% carry an invisible one
        with schema    visible defects are impossible, invisible ones are not

Costs: a free-form call is 0.0002, a schema-constrained call is 0.0004, because the sampler does
more work. A retry is another call at the free price.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

SCHEMA = {"vendor": "str", "invoice_date": "str:date", "total": "float"}

# A visible defect: the reply cannot be read, or cannot satisfy the schema.
VISIBLE = (
    ("truncated", 0.18),
    ("trailing_comma", 0.14),
    ("prose_prefix", 0.14),
    ("amount_as_string", 0.10),
    ("date_long_form", 0.08),
    ("missing_field", 0.06),
)

# An invisible defect: the reply is valid and about the wrong party.
WRONG_PARTY = 0.20

CASES = (
    ("Northwind Ltd", "Acme Freight", "2026-03-12", 1245.50),
    ("Blue Harbor", "Larkspur Ltd", "2026-02-28", 318.00),
    ("Meridian Group", "Northwind Ltd", "2026-04-02", 79.99),
    ("Larkspur Ltd", "Blue Harbor", "2026-01-15", 5600.00),
    ("Acme Freight", "Meridian Group", "2026-05-21", 42.10),
    ("Northwind Ltd", "Larkspur Ltd", "2026-06-30", 1000.00),
    ("Blue Harbor", "Acme Freight", "2026-03-01", 875.25),
    ("Meridian Group", "Blue Harbor", "2026-07-04", 250.00),
    ("Larkspur Ltd", "Meridian Group", "2026-08-19", 19.99),
    ("Acme Freight", "Northwind Ltd", "2026-09-09", 333.33),
)

MESSAGES = (
    "From: billing@{vendor_slug}\nTo: accounts@{buyer_slug}\nDate: {long_date}\n"
    "Subject: Invoice\n\nPlease find the invoice for {amount} issued by {vendor} to {buyer}.",
    "Invoice\nSeller: {vendor}\nBuyer: {buyer}\nIssued: {long_date}\nTotal due: {amount}\n",
    "Hi, {buyer} here. {vendor} invoiced us {amount} on {long_date}. Can you log it?",
    "Payment request from {vendor} to {buyer}, dated {long_date}, amount {amount}.",
)


@dataclass(frozen=True)
class Case:
    id: str
    text: str
    truth: dict
    buyer: str
    raw: str = ""


def _unit(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:13], 16) / float(16**13)


LONG_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def long_date(iso: str) -> str:
    year, month, day = iso.split("-")
    return f"{int(day)} {LONG_MONTHS[int(month) - 1]} {year}"


def build(seed: int = 2027) -> list[Case]:
    cases: list[Case] = []
    for index in range(30):
        vendor, buyer, date, total = CASES[index % len(CASES)]
        template = MESSAGES[index % len(MESSAGES)]
        text = template.format(
            vendor=vendor,
            buyer=buyer,
            vendor_slug=vendor.split()[0].lower(),
            buyer_slug=buyer.split()[0].lower(),
            long_date=long_date(date),
            amount=f"{total:,.2f}",
        )
        cases.append(
            Case(
                id=f"c{index + 1:02d}",
                text=text,
                truth={"vendor": vendor, "invoice_date": date, "total": total},
                buyer=buyer,
                raw=text,
            )
        )
    return cases


@dataclass
class Response:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float

    def __str__(self) -> str:
        return self.text


class ExtractionModel:
    """A model that is good at parsing and bad at knowing which party is which.

    `schema=None` samples free text, which is where the visible defects come from. Passing the
    schema makes the sampler emit a valid object — the same mechanism a structured-output API
    gives you — and leaves the extraction errors exactly as they were.
    """

    name = "extraction-model"
    COST_FREE = 0.0002
    COST_SCHEMA = 0.0004

    def __init__(self, cases: list[Case]) -> None:
        self.by_id = {case.id: case for case in cases}
        self.calls: list[dict] = []
        self._cost = 0.0
        self._latencies: list[float] = []

    def reset(self) -> None:
        self.calls.clear()
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

    def _payload(self, case: Case, attempt: int) -> dict:
        data = dict(case.truth)
        if _unit(case.id, "wrong_party") < WRONG_PARTY:
            # The classic extraction error: the buyer is the party the message is addressed to.
            data["vendor"] = case.buyer
        return data

    def complete(self, prompt: str, system: str | None = None, *, schema: dict | None = None) -> Response:
        match = re.search(r"\[(c\d{2})\]", prompt)
        case = self.by_id.get(match.group(1)) if match else None
        attempt = sum(1 for call in self.calls if call.get("case") == (case.id if case else None))

        if case is None:
            text = "{}"
        elif schema is not None:
            text = json.dumps(self._payload(case, attempt))
        else:
            text = self._free_text(case, attempt)

        cost = self.COST_SCHEMA if schema is not None else self.COST_FREE
        latency = 180.0 + (len(prompt) % 47) + (60.0 if schema is not None else 0.0)
        self._cost += cost
        self._latencies.append(latency)
        self.calls.append(
            {
                "case": case.id if case else None,
                "schema": schema is not None,
                "attempt": attempt,
                "tokens_in": max(1, len(prompt) // 4),
                "tokens_out": max(1, len(text) // 4),
                "cost_usd": cost,
                "latency_ms": latency,
                "output": text,
            }
        )
        return Response(
            text=text,
            tokens_in=max(1, len(prompt) // 4),
            tokens_out=max(1, len(text) // 4),
            latency_ms=latency,
            cost_usd=cost,
        )

    def _free_text(self, case: Case, attempt: int) -> str:
        data = self._payload(case, attempt)
        text = json.dumps(data, indent=2)

        roll = _unit(case.id, attempt, "defect")
        cursor = 0.0
        fired = None
        for name, probability in VISIBLE:
            cursor += probability
            if roll < cursor:
                fired = name
                break
        if fired is None:
            return text

        if fired == "truncated":
            return text[: max(12, int(len(text) * 0.55))]
        if fired == "trailing_comma":
            return re.sub(r"\n(\s*)\}", r",\n\1}", text, count=1)
        if fired == "prose_prefix":
            return "Sure! Here is the JSON:\n```json\n" + text + "\n```"
        if fired == "amount_as_string":
            data["total"] = f"{data['total']:,.2f}"
            return json.dumps(data, indent=2)
        if fired == "date_long_form":
            data["invoice_date"] = long_date(data["invoice_date"])
            return json.dumps(data, indent=2)
        if fired == "missing_field":
            data.pop("invoice_date", None)
            return json.dumps(data, indent=2)
        return text


def model(cases: list[Case]) -> ExtractionModel:
    return ExtractionModel(cases)
