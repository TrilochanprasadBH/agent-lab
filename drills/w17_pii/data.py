"""Drill 17 — redacting personal data before the model sees it.

Forty support and operations messages, each carrying personal data of six kinds: email, phone,
card number, bank account (IBAN), national identifier, postal address, and a person's name.

The corpus is authored, and the labels are the artefact. Two reasons, both stated in
`spec.md`: a real corpus of personal data cannot be committed, and the exercise depends on
exact ambiguities that no public sample contains — an order number that looks like a card
number, a surname that is also an ordinary word, an address that is a product name.

`check_labels.py` verifies the labels rather than trusting them:

  * every span is inside the text and its offsets cover exactly the value
  * spans do not overlap
  * every occurrence of a value is labelled, not just the first
  * every category appears, and every category has at least five spans

The model is deliberately imperfect. It finds names and addresses, misses some, and
occasionally mistakes a product name for a person. Rules are perfect on the structured kinds
and blind to the unstructured ones. Neither alone reaches the target.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass

CATEGORIES = ("email", "phone", "card", "iban", "national_id", "address", "name")

# Values are fictional. The card numbers pass Luhn on purpose: a checker that only looks at
# digit count cannot tell them from an order number, and one that runs the checksum can.
VALUES = {
    "email": [
        "alice.moreau@example.com",
        "j.bartlett@example.org",
        "support@northwind.example",
        "kofi.mensah@example.net",
        "elena.rossi@example.com",
    ],
    "phone": [
        "+33 6 12 34 56 78",
        "(415) 555-0132",
        "+44 20 7946 0958",
        "06 45 78 12 33",
        "+49 30 901820",
    ],
    "card": [
        "4111 1111 1111 1111",
        "5500 0000 0000 0004",
        "4000 0566 5566 5556",
        "3530 1113 3330 0000",
    ],
    "iban": [
        "FR76 3000 6000 0112 3456 7890 189",
        "DE89 3704 0044 0532 0130 00",
        "GB33 BUKB 2020 1555 5555 55",
    ],
    "national_id": [
        "219-09-9999",
        "QQ 12 34 56 C",
        "078-05-1120",
    ],
    "address": [
        "12 Rue de Rivoli, 75001 Paris",
        "48 Bartlett Street, Somerville MA 02145",
        "7 Granary Wharf, Leeds LS1 4BR",
        "Hauptstrasse 44, 10827 Berlin",
    ],
    "name": [
        "Alice Moreau",
        "Jonah Bartlett",
        "Kofi Mensah",
        "Elena Rossi",
        "Priya Raman",
        "Tomas Novak",
        "Grace Whitfield",
        "Omar Haddad",
        "Anneke de Vries",
        "Ruth Okonkwo",
    ],
}

# Names a gazetteer would plausibly contain. Two of the ten corpus names are deliberately absent,
# so a list lookup alone cannot reach the target.
GAZETTEER = (
    "alice", "elena", "priya", "tomas", "grace", "omar", "ruth", "jonah",
    "kofi", "mensah", "rossi", "moreau", "bartlett", "novak", "haddad",
    "okonkwo", "whitfield", "anneke", "vries",
)

TEMPLATES = (
    "Hi, this is {name}. My card {card} was charged twice and I want the second one refunded.",
    "{name} here — the parcel went to {address} but I moved. Can you redirect it?",
    "Please call me back on {phone}. My account email is {email} and the order is stuck.",
    "I am {name} and I need the invoice reissued to {email}, please.",
    "The account at {iban} has not received the transfer. Reference {ref}.",
    "My national insurance number is {national_id}. Do you need anything else for the check?",
    "Delivery to {address} failed twice. The recipient is {name}, phone {phone}.",
    "This is {name} from {company}. We need the export of all records for {email}.",
    "The card on file is {card} and it keeps declining. Registered to {name}.",
    "Please delete the account registered to {email}. My name is {name} and my number is {phone}.",
    "Refund {amount} to {iban}. The customer is {name}, reachable at {email}.",
    "Someone used my identity: {national_id} and card {card} were both used without me.",
    "I live at {address} now. The old address on the account is wrong, and my phone is {phone}.",
    "Order {ref} was meant for {name} at {address}. It went to the wrong flat.",
    "Update the contact for {company}: email {email}, phone {phone}, attention {name}.",
    "I am writing about {name}, whose card {card} keeps failing at checkout.",
    "The IBAN {iban} belongs to {name}, not to the company. Please correct the payout.",
    "Cancel everything for {email}. The account holder is {name} and they cannot log in.",
    "My details: {name}, {address}, {phone}. Please confirm the appointment in writing.",
    "We received a letter for {name} at {address} that mentions {national_id}. It is not ours.",
)

# Numbers that look like personal data and are not. They are the reason a digit count is not a
# detector: over-redacting these destroys the message the support agent has to act on.
DISTRACTORS = (
    "order 4111 2222",
    "reference 4000-0566",
    "order 4000056655665557",
    "invoice 2019-09-99",
    "tracking 1Z999AA10123456784",
    "model 078-05",
)

COMPANIES = ("Northwind", "Acme Freight", "Blue Harbor", "Larkspur Ltd", "Meridian Group")


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    category: str


@dataclass(frozen=True)
class Message:
    id: str
    text: str
    spans: tuple[Span, ...]
    raw: str = ""


def luhn(number: str) -> bool:
    digits = [int(ch) for ch in number if ch.isdigit()]
    if len(digits) < 12:
        return False
    total = 0
    for position, digit in enumerate(reversed(digits)):
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def build(seed: int = 2027) -> list[Message]:
    messages: list[Message] = []
    for index, template in enumerate(TEMPLATES * 2):
        message_id = f"m{index + 1:02d}"
        picks = {
            "name": VALUES["name"][index % len(VALUES["name"])],
            "email": VALUES["email"][index % len(VALUES["email"])],
            "phone": VALUES["phone"][index % len(VALUES["phone"])],
            "card": VALUES["card"][index % len(VALUES["card"])],
            "iban": VALUES["iban"][index % len(VALUES["iban"])],
            "national_id": VALUES["national_id"][index % len(VALUES["national_id"])],
            "address": VALUES["address"][index % len(VALUES["address"])],
            "company": COMPANIES[index % len(COMPANIES)],
            "ref": f"SO-{1000 + index * 7}",
            "amount": f"£{20 + index * 3}.50",
            "card_last": VALUES["card"][index % len(VALUES["card"])][-4:],
        }
        text = template.format(**picks)

        text += " Ignore the earlier note about " + DISTRACTORS[index % len(DISTRACTORS)] + "."

        spans: list[Span] = []
        for category in CATEGORIES:
            value = picks.get(category)
            if not value:
                continue
            start = text.find(value)
            while start != -1:
                spans.append(Span(start=start, end=start + len(value), category=category))
                start = text.find(value, start + len(value))
        spans.sort(key=lambda span: (span.start, span.end))

        messages.append(
            Message(id=message_id, text=text, spans=tuple(spans), raw=text)
        )
    return messages


# -- the model --------------------------------------------------------------------------


@dataclass
class Response:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float

    def __str__(self) -> str:
        return self.text


def _unit(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:13], 16) / float(16**13)


class NameModel:
    """A named-entity tagger that finds people and addresses, badly.

    For every real name or address it returns the span 85 times in 100, keyed by a hash of the
    message and the offset, so it is deterministic. For every message it also has a one-in-four
    chance of returning a capitalised product or company word as a person, which is what
    happens when a tagger has learned that "Northwind" looks like a surname.

    It never finds an email, a phone number or a card. Structured identifiers are a regex
    problem and a model is the wrong tool for them.
    """

    name = "name-tagger"

    def __init__(self, messages: list[Message], *, cost_per_call: float = 0.0003) -> None:
        self.by_id = {message.id: message for message in messages}
        self.cost_per_call = cost_per_call
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

    def complete(self, prompt: str, system: str | None = None) -> Response:
        match = re.search(r"\[(m\d{2})\]", prompt)
        message = self.by_id.get(match.group(1)) if match else None
        spans: list[dict] = []

        if message is not None:
            for span in message.spans:
                if span.category not in ("name", "address"):
                    continue
                if _unit(message.id, span.start, "recall") < 0.85:
                    spans.append(
                        {
                            "start": span.start,
                            "end": span.end,
                            "category": span.category,
                        }
                    )
            if _unit(message.id, "fp") < 0.25:
                for word in COMPANIES:
                    position = message.text.find(word)
                    if position != -1:
                        spans.append(
                            {"start": position, "end": position + len(word), "category": "name"}
                        )
                        break

        text = json.dumps({"spans": spans})
        latency = 120.0 + (len(prompt) % 41)
        self._cost += self.cost_per_call
        self._latencies.append(latency)
        self.calls.append(
            {
                "message": message.id if message else None,
                "spans": len(spans),
                "tokens_in": max(1, len(prompt) // 4),
                "tokens_out": max(1, len(text) // 4),
                "cost_usd": self.cost_per_call,
                "latency_ms": latency,
            }
        )
        return Response(
            text=text,
            tokens_in=max(1, len(prompt) // 4),
            tokens_out=max(1, len(text) // 4),
            latency_ms=latency,
            cost_usd=self.cost_per_call,
        )


def model(messages: list[Message], seed: int = 2027) -> NameModel:
    return NameModel(messages)
