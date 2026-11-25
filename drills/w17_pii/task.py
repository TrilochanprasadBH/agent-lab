"""Drill 17 — Redacting personal data before the model sees it.

Goal
    Find every piece of personal data in a message and say where it is, so a
    redaction step can replace it.

Return
    A dict with key "spans": a list of (start, end, category) tuples into the
    original text. Categories are the ones in `data.CATEGORIES`.

Run
    python3 run.py --drill w17_pii

Starting point
    Emails and card-shaped digit groups. The digit check counts sixteen digits
    and does not verify them, so it redacts order numbers; it never finds a name,
    an address, a phone number, an IBAN or a national identifier.

Full brief
    drills/w17_pii/spec.md
"""

from __future__ import annotations

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
DIGITS = re.compile(r"\b(?:\d[ -]?){15}\d\b")


def redact(message, model) -> dict:
    spans: list[tuple[int, int, str]] = []

    for match in EMAIL.finditer(message.text):
        spans.append((match.start(), match.end(), "email"))
    for match in DIGITS.finditer(message.text):
        spans.append((match.start(), match.end(), "card"))

    spans.sort()
    return {"spans": spans}
