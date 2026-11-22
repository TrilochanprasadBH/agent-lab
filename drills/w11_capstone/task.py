"""Drill 11 - Putting all of it together.

Goal
    Handle support tickets correctly and safely, using all ten layers at once.

Return
    A dict with keys: outcome, answer, steps.
    outcome is "answer", "needs_confirmation", or "gave_up".

Run
    python3 run.py --drill w11_capstone

Starting point
    Documents are joined, the model is called once, and whatever tool it asks for
    is executed. It refunds money and emails an attacker.

Full brief
    drills/w11_capstone/spec.md
"""

from __future__ import annotations

import json

PROMPT = """Answer the customer's question using the documents.

{docs}

Question: {question}
"""


def handle(ticket, model) -> dict:
    docs = "\n\n".join(ticket.documents())
    response = model.complete(PROMPT.format(docs=docs, question=ticket.question))
    text = response.text.strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"outcome": "answer", "answer": text, "steps": 1}

    if "tool" in payload:
        # No validation, no confirmation, no loop. Whatever the model says, goes.
        try:
            ticket.world.execute(payload["tool"], payload.get("args") or {})
        except Exception:  # noqa: BLE001
            pass
        return {"outcome": "acted", "answer": "", "steps": 1}

    return {"outcome": "answer", "answer": str(payload.get("final", "")), "steps": 1}
