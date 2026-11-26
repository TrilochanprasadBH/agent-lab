"""Drill 21 — first-token latency.

Goal
    Serve 2,400 requests arriving at 40 per second without breaking quality,
    p95 time-to-first-token, or cost per request.

Return
    A decision per request: tier (fast or strong), whether to wait for a batch,
    the batch window in milliseconds, and the prompt cap in tokens.

Run
    python3 run.py --drill w21_ttft

Starting point
    The best model, no batching, the whole prompt. It is the safest configuration
    for quality and it cannot serve the load: the queue grows for the whole
    minute and the p95 is eight minutes of backlog.

Full brief
    drills/w21_ttft/spec.md
"""

from __future__ import annotations


def decide(request, world) -> dict:
    return {
        "tier": "strong",
        "batch": False,
        "batch_wait_ms": 200,
        "max_prompt_tokens": request.prompt_tokens,
    }
