"""Reference solution for the first-token latency drill.

Three decisions, each forced by one of the gates.

**Route by the difficulty flag.** The strong model is accurate on 98% of requests and the fast one
on 79%, and the target is 92%. A third of the traffic is hard, and the fast model is right on 42%
of it. Sending the hard third to the strong model and the rest to the fast one lands at 96% at
about half the cost of routing everything to the strong model.

**Batch everything, and size the window for the slow tier.** A batch of eight costs one pass, so
it is eight times the throughput at an eighth of the cost. The window is the trade: 200ms is too
short for the strong tier, whose requests arrive at 12 per second and need a batch of six to keep
up, so its queue grows and the p95 goes to seven seconds. 400ms fills both tiers' batches and
still leaves the p95 well inside the budget.

**Do not truncate.** Truncating to 700 tokens cuts p95 by about 35ms and quality by 8 points,
because the evidence sits at an offset the server never sees. It is the one lever here that looks
like a latency fix and is a quality loss.

The result: quality 95.8%, p95 524ms, $0.00049 per request, against gates of 92%, 900ms and
$0.0008.
"""

from __future__ import annotations

BATCH_WAIT_MS = 400


def decide(request, world) -> dict:
    return {
        "tier": "strong" if request.hard else "fast",
        "batch": True,
        "batch_wait_ms": BATCH_WAIT_MS,
        "max_prompt_tokens": request.prompt_tokens,
    }
