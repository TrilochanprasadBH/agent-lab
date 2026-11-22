"""Drill 04 - Turning text into a safe tool call.

Goal
    Convert the model's text into a validated tool call, or a named rejection.

Return
    A dict with keys: outcome, tool.
    outcome is one of: ok, unknown_tool, missing_param, bad_type, bad_enum,
    unknown_param, needs_confirmation, no_call.

Run
    python3 run.py --drill w04_tools

Starting point
    The text is parsed with json.loads and the named tool is executed directly.
    No validation, no confirmation, no loop.

Full brief
    drills/w04_tools/spec.md
"""

from __future__ import annotations

import json
import re

PROMPT = """You have these tools:
- lookup_customer(customer_id)
- list_orders(customer_id, status)
- get_order(order_id)
- refund_order(order_id, amount)
- delete_account(customer_id)

Return one JSON object: {{"tool": ..., "args": {{...}}}}

Request: {request}
"""


def handle(case, model) -> dict:
    response = model.complete(PROMPT.format(request=case.request))
    text = response.text.strip()

    try:
        call = json.loads(text)
    except json.JSONDecodeError:
        return {"outcome": "no_call", "tool": None}

    name = call.get("tool")
    args = call.get("args") or {}

    try:
        case.world.execute(name, args)
        return {"outcome": "ok", "tool": name}
    except Exception:  # noqa: BLE001
        return {"outcome": "error", "tool": name}
