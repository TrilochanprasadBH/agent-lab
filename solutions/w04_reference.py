"""Reference solution for drill 4 — read this after trying your own.

The model produces text. A tool call is a data structure you construct from that
text, and it has to pass through a gate before it is allowed to touch the world.

Five moves:

  1. Degrade gracefully on the shape. Strip fences, ignore prose before the first
     `{`, and if the object is truncated, balance it. Refusal text is not an
     error, it is `no_call`.
  2. Unwrap double-encoded arguments. A JSON string where an object belongs is
     common, and it is one `json.loads` away from fine.
  3. Validate against the schema before execution, never after. Type coercion is
     narrow: `"3"` is an integer, `"3.5"` is not; a number is not a string id.
  4. Treat unknown parameters as errors, not noise. Silently dropping them is how
     a typo becomes a wrong write.
  5. Confirmation is a human decision. The model asserting `"confirm": true` is
     evidence of the model's opinion, not of consent. It never opens the gate.
"""

from __future__ import annotations

import json
import re

from agentlab.tools import Param, Tool, ToolRegistry

TOOLS = {
    "lookup_customer": (Tool(
        "lookup_customer", "look up a customer record",
        (Param("customer_id", "string", description="customer id"),),
        lambda args: args,
    )),
}

SAFE_TOOLS = ("lookup_customer", "list_orders", "get_order")


def _close_json(fragment: str) -> str:
    stack: list[str] = []
    in_string = False
    escaped = False
    for ch in fragment:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch == "{":
            stack.append("}")
        elif ch == "[":
            stack.append("]")
        elif ch in "}]" and stack:
            stack.pop()

    text = fragment
    if in_string:
        text += '"'
    text = text.rstrip()
    while text and text[-1] in ".,:":
        text = text[:-1].rstrip()
    return text + "".join(reversed(stack))


def parse_call(text: str) -> dict | None:
    if not text:
        return None

    fenced = re.search(r"```(?:json)?\s*(.*?)(?:```|$)", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)

    start = text.find("{")
    if start == -1:
        return None
    body = text[start:]

    candidates = [body]
    end = body.rfind("}")
    if end > 0:
        candidates.append(body[: end + 1])
    candidates.append(_close_json(body))

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def unwrap_args(args) -> dict | None:
    if args is None:
        return {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return None
    return args if isinstance(args, dict) else None


def build_registry(case) -> ToolRegistry:
    """One registry per case, wired to the case's own world."""
    world = case.world
    registry = ToolRegistry()
    registry.add(Tool(
        "lookup_customer", "look up a customer record",
        (Param("customer_id", "string"),),
        lambda a: world.execute("lookup_customer", a),
    ))
    registry.add(Tool(
        "list_orders", "list orders for a customer",
        (Param("customer_id", "string"), Param("status", "string", required=False,
                                               enum=("pending", "shipped", "refunded"))),
        lambda a: world.execute("list_orders", a),
    ))
    registry.add(Tool(
        "get_order", "fetch one order",
        (Param("order_id", "string"),),
        lambda a: world.execute("get_order", a),
    ))
    registry.add(Tool(
        "refund_order", "refund an order",
        (Param("order_id", "string"), Param("amount", "number")),
        lambda a: world.execute("refund_order", a),
        dangerous=True,
    ))
    registry.add(Tool(
        "delete_account", "delete a customer account",
        (Param("customer_id", "string"),),
        lambda a: world.execute("delete_account", a),
        dangerous=True,
    ))
    return registry


def handle(case, model) -> dict:
    response = model.complete(
        "Return one JSON object: {\"tool\": ..., \"args\": {...}}\n\n"
        f"Request: {case.request}\n"
    )

    call = parse_call(response.text)
    if call is None:
        return {"outcome": "no_call", "tool": None}

    name = call.get("tool")
    args = unwrap_args(call.get("args"))
    if args is None:
        return {"outcome": "bad_arguments", "tool": name}

    registry = build_registry(case)
    result = registry.call(name, args, confirmed=False)

    if result["ok"]:
        return {"outcome": "ok", "tool": name}
    return {"outcome": result["kind"], "tool": name}
