"""Reference solution for the constrained-JSON drill.

One call per case, with the schema passed to the sampler. That is the whole implementation, and
it is the point: a structured-output API turns "ask nicely and hope" into a guarantee about
*shape*, at twice the price of a free call.

What it does not do is check the content. Three of the thirty cases name the buyer instead of the
seller, and this solution repeats those three errors with perfect JSON. `spec.md` closes on that,
because a drill that ends with 100% validity and no mention of it would teach the wrong lesson.
"""

from __future__ import annotations

import json

from drills.w18_constrained_json.data import SCHEMA


def extract(case, model) -> dict:
    reply = model.complete(f"[{case.id}] {case.text}", schema=SCHEMA)
    try:
        payload = json.loads(reply.text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}
