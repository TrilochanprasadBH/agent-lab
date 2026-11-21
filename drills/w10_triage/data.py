"""Sixty agent traces and the six things that actually go wrong.

Every trace contains the word "error" and most contain a keyword belonging to some
*other* failure mode, because real logs are full of noise and a grep is not a
diagnosis. The primary error line is the one that matters; the rest is context.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

CAUSES = (
    "loop",
    "context_overflow",
    "bad_tool_arg",
    "auth",
    "timeout",
    "wrong_tool",
)

PRIMARY = {
    "loop": "error: no progress after 6 steps — the last 5 steps were identical",
    "context_overflow": "error: maximum context length is 131072 tokens, prompt was 148200",
    "bad_tool_arg": "error: validation failed: missing_param order_id",
    "auth": "error: HTTP 401 unauthorized — token expired at 14:02",
    "timeout": "error: deadline exceeded after 30.0s while waiting for tool response",
    "wrong_tool": "error: tool `refund_order` does not satisfy the request (expected a status lookup)",
}

DISTRACTORS = {
    "loop": "note: timeout was not reached; auth was fine",
    "context_overflow": "note: no timeout and no auth problem; the schema was valid",
    "bad_tool_arg": "note: the retry loop did not run; context was well within limits",
    "auth": "note: no timeout occurred and the context was small",
    "bad_tool_arg2": "note: authorization was not involved",
    "timeout": "note: the loop exited cleanly; authorization succeeded",
    "wrong_tool": "note: context length was fine; no timeout",
}

STEPS = {
    "loop": [
        "step 1: tool get_order({'order_id': 'o8712'}) -> ok",
        "step 2: tool get_order({'order_id': 'o8712'}) -> ok",
        "step 3: tool get_order({'order_id': 'o8712'}) -> ok",
        "step 4: tool get_order({'order_id': 'o8712'}) -> ok",
    ],
    "context_overflow": [
        "step 1: retrieved 42 documents (148200 tokens)",
        "step 2: preparing prompt for model tier: strong",
    ],
    "bad_tool_arg": [
        "step 1: model emitted tool call get_order({})",
        "step 2: schema check rejected the call",
    ],
    "auth": [
        "step 1: calling billing API for invoice 8712",
        "step 2: response 401",
    ],
    "timeout": [
        "step 1: calling search index",
        "step 2: still waiting after 30s",
    ],
    "wrong_tool": [
        "step 1: user asked for the shipping status of o8712",
        "step 2: model chose refund_order",
    ],
}


@dataclass(frozen=True)
class Trace:
    doc_id: str
    text: str
    truth: str
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.text)


def build() -> list[Trace]:
    rng = random.Random(2027)
    traces: list[Trace] = []
    counter = 0

    for cause in CAUSES:
        for _ in range(10):
            counter += 1
            steps = STEPS[cause]
            distractor = rng.choice(list(DISTRACTORS.values()))
            text = "\n".join(
                [
                    f"trace {counter:03d}",
                    f"goal: handle a request from customer c{100 + rng.randint(0, 9)}",
                    *steps,
                    distractor,
                    PRIMARY[cause],
                ]
            )
            traces.append(Trace(doc_id=f"tr{counter:03d}", text=text, truth=cause))

    rng.shuffle(traces)
    return traces


TRACES = build()


def corpus() -> list[Trace]:
    return list(TRACES)


def causes() -> tuple[str, ...]:
    return CAUSES
