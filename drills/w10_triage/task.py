"""Drill 10 — triage from traces.

THIS IS THE FILE YOU EDIT.

Target: 90% correct root causes across 60 traces.

Allowed labels:

    loop  context_overflow  bad_tool_arg  auth  timeout  wrong_tool

Read the trace. Every one contains the word "error", and most contain a keyword
that belongs to a different cause. The baseline below greps for the first match
and is wrong about two thirds of the time.
"""

from __future__ import annotations


def classify(trace, model) -> str:
    text = trace.text.casefold()
    if "timeout" in text:
        return "timeout"
    if "401" in text:
        return "auth"
    return "loop"
