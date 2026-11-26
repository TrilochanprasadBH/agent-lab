"""Drill 20 — Debug the wrong answer.

Goal
    Given a failing question, its trace, and the index behind it, name the first
    stage where the evidence disappeared and the repair that follows from it.

Return
    {"stage": one of data.STAGES, "fix": the repair for that stage}

Run
    python3 run.py --drill w20_debug

Starting point
    Blame the model. It is the last thing in the pipeline, it is the component
    everyone distrusts, and "the answer is wrong" is the only symptom the user
    ever sees. It is right about one case in seven.

Full brief
    drills/w20_debug/spec.md
"""

from __future__ import annotations


def diagnose(case, model) -> dict:
    return {"stage": "generation", "fix": "ground"}
