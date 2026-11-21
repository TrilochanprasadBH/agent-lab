"""Reference solution for drill 8 — read this after trying your own.

Three ways to route, and they are worth trying in order:

  1. **By shape of the request.** A lookup names an identifier and asks for one
     attribute. Reasoning asks "why", "compare", "design", "explain". A keyword
     classifier gets most of the way in an afternoon, and it is free.
  2. **By consequence of being wrong.** A wrong shipping status is a support
     ticket. A wrong refund decision is money. Escalate by stakes, not by
     difficulty.
  3. **By measured confidence, when you have one.** A cheap call can report a
     confidence; below the threshold, re-ask the expensive tier. That is more
     accurate than keywords and more expensive than keywords, and you should only
     build it once keywords have stopped paying.

This solution uses (1): reasoning verbs escalate, lookups do not.
"""

from __future__ import annotations

REASONING = (
    "why", "compare", "design", "explain", "debug", "root cause",
    "tradeoff", "trade-off", "should we", "recommend", "evaluate",
    "how do we", "how should",
)


def answer(query, model) -> dict:
    text = query.text.casefold()
    hard = any(marker in text for marker in REASONING)
    tier = "strong" if hard else "cheap"

    prompt = f"tier: {tier}\nAnswer the question in one sentence.\n{query.text}\n"
    response = model.complete(prompt)
    return {"answer": response.text.strip(), "tier": tier}
