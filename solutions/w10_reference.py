"""Reference solution for drill 10 — read this after trying your own.

The move is not "add more keywords". It is **read the right line**.

Two things make triage work:

  1. **Find the primary error.** The last line that starts with `error:` is the
     failure. Everything above it is the path that led there, and everything else
     in the log is someone else's word for a different problem.
  2. **Order by specificity.** `no progress after 6 steps` is a loop even though
     the trace also mentions retries. `does not satisfy the request` is a wrong
     tool even though the tool name contains `refund`. Match the specific
     evidence before the general.

A rule set is a decision list, and a decision list is only as good as its order.
That is true of eval rubrics, guardrails, and router thresholds too.
"""

from __future__ import annotations

import re

# Most specific first. Order is the whole design.
RULES = (
    ("loop", r"no progress after|steps were identical|identical call"),
    ("context_overflow", r"maximum context length|prompt was \d+ tokens"),
    ("bad_tool_arg", r"missing_param|bad_type|validation failed|bad_enum"),
    ("auth", r"\b40[13]\b|unauthorized|token expired"),
    ("wrong_tool", r"does not satisfy the request|wrong tool|expected a .* lookup"),
    ("timeout", r"deadline exceeded|timed out|still waiting after"),
)


def primary_error(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip().casefold().startswith("error:")]
    return lines[-1].casefold() if lines else text.casefold()


def classify(trace, model) -> str:
    error = primary_error(trace.text)
    for label, pattern in RULES:
        if re.search(pattern, error):
            return label

    # Nothing matched the primary line: fall back to the whole trace, but only
    # now, and never let the fallback outrank a specific match.
    text = trace.text.casefold()
    for label, pattern in RULES:
        if re.search(pattern, text):
            return label
    return "timeout"
