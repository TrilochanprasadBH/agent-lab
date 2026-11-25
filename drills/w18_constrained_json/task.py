"""Drill 18 — Always-valid JSON.

Goal
    Turn one invoice message into an object that satisfies the schema, without
    losing the content the schema is supposed to carry.

Return
    A dict with keys vendor (str), invoice_date (str, YYYY-MM-DD) and total
    (float).

Run
    python3 run.py --drill w18_constrained_json

Starting point
    The free-form reply is passed to json.loads and whatever comes back is
    returned. When it does not parse, the answer is an empty dict: valid-ish,
    and useless. Nothing checks the schema, and nothing checks the content.

Full brief
    drills/w18_constrained_json/spec.md
"""

from __future__ import annotations

import json


def extract(case, model) -> dict:
    reply = model.complete(f"[{case.id}] {case.text}")
    try:
        data = json.loads(reply.text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
