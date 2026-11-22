"""Drill 05 - Running a task that takes several steps.

Goal
    Run a multi-step task to a correct answer, or stop deliberately when stuck.

Return
    A dict with keys: kind, text, steps.
    kind is "answer" or "gave_up". steps is the number of model calls you made.

Run
    python3 run.py --drill w05_loop

Starting point
    The model is called once and whatever comes back is returned. No tool results
    reach the next call because there is no next call.

Full brief
    drills/w05_loop/spec.md
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
