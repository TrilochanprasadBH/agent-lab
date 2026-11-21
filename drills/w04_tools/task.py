"""Drill 4 — tool calls that arrive wrong.

THIS IS THE FILE YOU EDIT.

Target: 90% correct outcomes, and zero state-changing calls executed without
confirmation.

The model hands you text. Sometimes it is a clean tool call, sometimes it is a
fenced block, sometimes it is truncated, sometimes the arguments are a JSON
string, sometimes it is a refusal. Your job is to turn that text into either a
validated call or a specific, named rejection.

Rules of the world:
  - `case.world.execute(name, args)` runs a tool and does not validate anything.
  - Anything that changes state (refunds, deletes) must never run on the model's
    say-so. A model writing `"confirm": true` is not a human confirming.
  - The score checks what actually ran, not what you claim ran.
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
