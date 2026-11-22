"""Drill 01 - Turning model output into data.

Goal
    Extract four fields from invoices, when the model's output is malformed about
    half the time.

Return
    A dict with keys: vendor, invoice_date, currency, subtotal, tax, total.
    invoice_date is ISO 8601 (YYYY-MM-DD). currency is a three-letter code.

Run
    python3 run.py --drill w01_extraction

Starting point
    The response is parsed with json.loads. Anything wrapped in prose, truncated,
    or containing a trailing comma is thrown away.

Full brief
    drills/w01_extraction/spec.md
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
