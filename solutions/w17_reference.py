"""Reference solution for the PII drill.

Four layers, in order of how much they can be trusted:

  1. **Checksum.** A sixteen-digit number is a card only if it passes Luhn. This is what
     separates `4111 1111 1111 1111` from an order number, and it costs nothing.
  2. **Shape.** Emails, phones, IBANs and national identifiers have shapes narrow enough to
     match with a pattern and still be precise. The IBAN is validated by length, the phone by
     counting digits after stripping punctuation.
  3. **Context.** A capitalised word is a name if a gazetteer contains it, or if the sentence
     says so ("this is", "my name is", "attention"). Adjacent capitalised words are joined, so
     "Alice Moreau" is one span rather than two.
  4. **The model.** The tagger finds addresses well and names reasonably. Every span it returns
     is checked: it must be inside the text, it must not already be covered, and a span it
     labels a person must not be a company word.

The union is the answer. No single layer reaches the target, and each one that is removed costs
recall in the category it handled.
"""

from __future__ import annotations

import re

from drills.w17_pii.data import CATEGORIES, GAZETTEER, luhn

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

PHONE = re.compile(
    r"(?:\+\d{1,3}[\s.-]?(?:\(\d\)[\s.-]?)?|\(\d{3}\)\s?|\b0\d[\s.-]?)"
    r"(?:\d[\s.-]?){6,12}\d"
)

IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b")

NATIONAL_ID = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b[A-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-Z]\b")

CARD_GROUP = re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b")

# Two address shapes, both conservative: a house number followed by a street name and a
# postcode, or the same with a UK-style postcode. A false positive here is over-redaction, so
# the patterns require the postcode rather than inferring one.
ADDRESS = re.compile(
    r"\b\d{1,4}\s+[A-Z][\w'-]+(?:\s+[\w'-]+){0,4},\s*[A-Z]{0,3}\s?\d{4,5}\b"
    r"|\b\d{1,4}\s+[A-Z][\w'-]+(?:\s+[\w'-]+){0,4},\s*[A-Z][A-Za-z]+\s?[A-Z]{1,2}\d{1,2}\s?\d[A-Z]{2}\b"
)

CONTEXT = re.compile(
    r"(?:this is|my name is|name is|attention|from|recipient is|holder is|customer is)\s+"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})"
)

CAPITALISED = re.compile(r"\b[A-Z][a-z]{2,}\b")


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def _structured(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []

    for match in EMAIL.finditer(text):
        spans.append((match.start(), match.end(), "email"))

    for match in CARD_GROUP.finditer(text):
        numbers = _digits(match.group(0))
        if len(numbers) == 16 and luhn(numbers):
            spans.append((match.start(), match.end(), "card"))

    for match in IBAN.finditer(text):
        compact = re.sub(r"\s", "", match.group(0))
        if 15 <= len(compact) <= 34 and compact[:2].isalpha() and compact[2:4].isdigit():
            spans.append((match.start(), match.end(), "iban"))

    for match in NATIONAL_ID.finditer(text):
        spans.append((match.start(), match.end(), "national_id"))

    for match in PHONE.finditer(text):
        if 9 <= len(_digits(match.group(0))) <= 15:
            spans.append((match.start(), match.end(), "phone"))

    for match in ADDRESS.finditer(text):
        spans.append((match.start(), match.end(), "address"))

    return spans


def _names(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    taken = [(start, end) for start, end, _ in _structured(text)]

    def free(start: int, end: int) -> bool:
        return all(end <= left or start >= right for left, right in taken)

    for match in CONTEXT.finditer(text):
        start, end = match.start(1), match.end(1)
        if free(start, end):
            spans.append((start, end, "name"))
            taken.append((start, end))

    # A run of capitalised words where at least one is in the gazetteer.
    words = list(CAPITALISED.finditer(text))
    for position, match in enumerate(words):
        if match.group(0).lower() not in GAZETTEER:
            continue
        start, end = match.start(), match.end()
        cursor = position
        while cursor + 1 < len(words) and words[cursor + 1].start() == end + 1:
            end = words[cursor + 1].end()
            cursor += 1
        back = position
        while back > 0 and words[back - 1].end() == start - 1:
            start = words[back - 1].start()
            back -= 1
        if free(start, end):
            spans.append((start, end, "name"))
            taken.append((start, end))

    return spans


def redact(message, model) -> dict:
    spans = _structured(message.text) + _names(message.text)

    reply = model.complete(f"[{message.id}] {message.text}")
    import json

    try:
        payload = json.loads(reply.text)
    except json.JSONDecodeError:
        payload = {"spans": []}

    for row in payload.get("spans", []):
        start = int(row.get("start", -1))
        end = int(row.get("end", -1))
        category = str(row.get("category", ""))
        if category not in CATEGORIES:
            continue
        if not 0 <= start < end <= len(message.text):
            continue
        if not message.text[start:end].strip():
            continue
        overlapping = [
            (position, span)
            for position, span in enumerate(spans)
            if start < span[1] and end > span[0]
        ]
        if overlapping:
            # A model span that contains the spans already found replaces them, but only when it
            # is a person or an address: it must never overwrite an email or a card number.
            replaceable = category in ("name", "address") and all(
                existing[2] in ("name", "address") for _, existing in overlapping
            )
            contains_all = all(start <= span[0] and end >= span[1] for _, span in overlapping)
            longer = (end - start) > max(span[1] - span[0] for _, span in overlapping)
            if not (replaceable and contains_all and longer):
                continue
            drop = {position for position, _ in overlapping}
            spans = [span for position, span in enumerate(spans) if position not in drop]

        spans.append((start, end, category))

    spans.sort()
    return {"spans": spans}
