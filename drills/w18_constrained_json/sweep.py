#!/usr/bin/env python3
"""Compare the four ways of getting JSON out of this model.

    python3 drills/w18_constrained_json/sweep.py

  parse only     call it, json.loads, give up on failure           1 call
  repair         fix trailing commas, strip prose, coerce strings   1 call
  retry          call again while the object is invalid             up to 3 calls
  schema         pass the schema to the sampler                    1 call, 2x price

Every number in `spec.md` comes from here. The last column is the one that matters: an object can
be valid and name the wrong party, and only a check outside the model catches that.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from drills.w18_constrained_json import data  # noqa: E402
from drills.w18_constrained_json.drill import correct, validate  # noqa: E402


def parse_only(case, model):
    reply = model.complete(f"[{case.id}] {case.text}")
    try:
        return json.loads(reply.text)
    except json.JSONDecodeError:
        return {}


def repair(case, model):
    reply = model.complete(f"[{case.id}] {case.text}")
    text = reply.text
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    text = text[start : end + 1]
    text = re.sub(r",\s*}", "}", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def retry(case, model, attempts: int = 3):
    payload = {}
    for _ in range(attempts):
        reply = model.complete(f"[{case.id}] {case.text}")
        try:
            payload = json.loads(reply.text)
        except json.JSONDecodeError:
            continue
        if not validate(payload):
            return payload
    return payload if isinstance(payload, dict) else {}


def schema(case, model):
    reply = model.complete(f"[{case.id}] {case.text}", schema=data.SCHEMA)
    try:
        return json.loads(reply.text)
    except json.JSONDecodeError:
        return {}


STRATEGIES = (
    ("parse only", parse_only),
    ("repair", repair),
    ("retry x3", retry),
    ("schema", schema),
)


def main() -> int:
    cases = data.build()
    print()
    print(f" {len(cases)} cases, schema {data.SCHEMA}")
    print()
    print(f" {'strategy':<12}{'valid':>8}{'correct':>9}{'invisible':>11}{'calls/case':>12}{'cost':>9}")
    for name, strategy in STRATEGIES:
        model = data.model(cases)
        valid = good = 0
        for case in cases:
            payload = strategy(case, model)
            if not validate(payload):
                valid += 1
                good += 1 if correct(payload, case.truth) else 0
        n = len(cases)
        print(
            f" {name:<12}{valid / n:>7.1%}{good / n:>9.1%}{(valid - good) / n:>11.1%}"
            f"{model.n_calls / n:>12.2f}${model.cost_usd:>8.4f}"
        )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
