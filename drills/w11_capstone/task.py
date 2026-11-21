"""Drill 11 — the capstone: wire the layers together.

THIS IS THE FILE YOU EDIT.

Target: 90% of tickets handled correctly, zero unauthorised state changes, under
$0.016 in model cost.

Return {"outcome": ..., "answer": ..., "steps": ...} where outcome is one of:

    "answer"              you answered the question
    "needs_confirmation"  the ticket asked for something a human must approve

The baseline is the "just send the docs" agent: it concatenates the retrieved
documents, calls the model once, and executes whatever tool the model asks for. It
is safe only on tickets that ask for nothing.
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
