"""Reference solution for drill 5 — read this after trying your own.

A loop is four decisions and a lot of discipline:

  1. **What the model sees.** Its own history of calls and the *results*, not just
     the original question. A model without the observation will re-ask.
  2. **When to stop successfully.** A `final` payload, parsed and validated.
  3. **When to stop unsuccessfully.** Step budget, and — the one people skip —
     repeated identical calls. A model that loops on the same call will do it
     forever, and every iteration costs money.
  4. **What to do with an error.** Feed it back. Errors are observations; the
     model can often correct itself if you let it see the message. Swallowing
     them produces a confident wrong answer.

Note what `gave_up` does for the score: stopping deliberately is a correct
outcome. An agent that knows it is stuck is worth more than one that invents an
answer.
"""

from __future__ import annotations

import json
import re

from agentlab.tools import Param, Tool, ToolRegistry

SYSTEM = "You have tools. Call one per turn or answer with {\"final\": ...}."


def _parse(text: str) -> dict | None:
    fenced = re.search(r"```(?:json)?\s*(.*?)(?:```|$)", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    if start == -1:
        return None
    try:
        value = json.loads(text[start : text.rfind("}") + 1])
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _registry(world) -> ToolRegistry:
    registry = ToolRegistry()
    registry.add(Tool(
        "find_customer", "find a customer by exact name",
        (Param("name", "string"),),
        lambda a: world.execute("find_customer", a),
    ))
    registry.add(Tool(
        "list_orders", "list a customer's orders",
        (Param("customer_id", "string"),
         Param("status", "string", required=False,
               enum=("pending", "shipped", "refunded"))),
        lambda a: world.execute("list_orders", a),
    ))
    registry.add(Tool(
        "get_order", "fetch one order",
        (Param("order_id", "string"),),
        lambda a: world.execute("get_order", a),
    ))
    return registry


def solve(case, model) -> dict:
    registry = _registry(case.world)
    history: list[str] = []
    seen: set[str] = set()

    for step in range(1, case.max_steps + 1):
        prompt = [
            SYSTEM,
            f"Request: {case.request}",
            "",
            "History:" if history else "History: (nothing yet)",
            *history,
        ]
        response = model.complete("\n".join(prompt))
        payload = _parse(response.text)

        if payload is None:
            history.append("observation: your last message was not a JSON object")
            continue

        if "final" in payload:
            return {"kind": "answer", "text": str(payload["final"]), "steps": step}

        name = payload.get("tool")
        args = payload.get("args") or {}
        if not isinstance(args, dict):
            args = {}

        signature = f"{name}:{json.dumps(args, sort_keys=True)}"
        if signature in seen:
            return {
                "kind": "gave_up",
                "text": f"repeated the same call: {name}",
                "steps": step,
            }
        seen.add(signature)

        outcome = registry.call(name, args)
        if outcome["ok"]:
            history.append(f"observation: {name} -> {json.dumps(outcome['result'])[:400]}")
        else:
            history.append(f"observation: {name} failed ({outcome['kind']}): {outcome['error']}")

    return {"kind": "gave_up", "text": "step budget exhausted", "steps": case.max_steps}
