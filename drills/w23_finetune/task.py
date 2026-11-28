"""Drill 23 — Fine-tune, retrieve, or prompt.

Goal
    Choose the cheapest architecture that clears the quality bar, given a
    scenario's volume, constraints and measured quality.

Return
    One of "prompting", "rag", "finetune", "none".

Run
    python3 run.py --drill w23_finetune

Starting point
    Retrieve. It is the answer the industry gives by default, it is genuinely
    the right answer for a real share of these scenarios, and it is wrong for
    the rest.

Full brief
    drills/w23_finetune/spec.md
"""

from __future__ import annotations


def choose(scenario, model) -> str:
    return "rag"
