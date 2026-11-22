"""Drill 10 - Naming the cause of a failure.

Goal
    Identify the root cause of an agent failure from its trace.

Return
    One of: loop, context_overflow, bad_tool_arg, auth, timeout, wrong_tool.

Run
    python3 run.py --drill w10_triage

Starting point
    The whole trace is searched for keywords. Every trace contains several, so the
    first match is usually wrong.

Full brief
    drills/w10_triage/spec.md
"""

from __future__ import annotations


def classify(trace, model) -> str:
    text = trace.text.casefold()
    if "timeout" in text:
        return "timeout"
    if "401" in text:
        return "auth"
    return "loop"
