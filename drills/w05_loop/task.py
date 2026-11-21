"""Drill 5 — the agent loop.

THIS IS THE FILE YOU EDIT.

Target: 90% correct, every case inside its step budget.

Implement `solve(case, model) -> {"kind", "text", "steps"}`.

  kind   "answer" if you produced an answer, "gave_up" if you stopped on purpose
  text   the answer text, or your reason for stopping
  steps  how many model calls you made

The model has no memory. If you do not put the tool result into the next prompt,
the model cannot use it, and the model will happily ask for the same thing again.

The baseline calls the model once and returns whatever it said.
"""

from __future__ import annotations

import json


def solve(case, model) -> dict:
    response = model.complete(f"Request: {case.request}\n")
    text = response.text.strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"kind": "answer", "text": text, "steps": 1}

    if "final" in payload:
        return {"kind": "answer", "text": str(payload["final"]), "steps": 1}

    return {"kind": "answer", "text": text, "steps": 1}
