"""Drill 1 — structured extraction from messy invoices.

THIS IS THE FILE YOU EDIT.

Target: 90% field accuracy, under $0.030 total, zero crashes.
Run:    python3 run.py

The model returns JSON most of the time. The rest of the time it returns prose,
a truncated object, numbers as strings, the wrong party, or a refusal. Your job
is not to write a better prompt. Your job is to build the layer that turns an
unreliable response into a trustworthy record.
"""

from __future__ import annotations

import json
import re

PROMPT = """Extract the invoice fields below as JSON with keys:
vendor, invoice_date (ISO 8601), currency (ISO 4217), subtotal, tax, total.

Document:
{doc}
"""

FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def extract(invoice, model) -> dict:
    doc = invoice.raw
    response = model.complete(PROMPT.format(doc=doc))
    text = response.text.strip()

    # A junior-level cleanup: handle the obvious wrappers.
    fenced = FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Last resort: grab anything that looks like an object.
    match = OBJECT.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    return {}
