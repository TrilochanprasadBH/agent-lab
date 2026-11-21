"""Reference solution for drill 11 — read this after trying your own.

Ten things have to be true at once. Each one is a drill you have already done.

  1. **Select.** Not every candidate document is evidence. Pack what the question
     needs and leave the rest out (drill 3).
  2. **Sanitise.** Retrieved text is untrusted. Strip instruction-shaped sentences
     before the model sees them (drill 9).
  3. **Validate.** The model's tool call is text. It becomes a call only after the
     schema accepts it (drill 4).
  4. **Gate.** A state-changing action needs a human, and the model writing
     `confirm: true` is not a human (drills 4 and 9).
  5. **Observe.** Feed the tool result back, or the model will ask again (drill 5).
  6. **Bound the loop.** Steps and repeats, or a bad ticket burns the budget
     (drill 5).
  7. **Answer only when grounded.** If the evidence is not in the prompt, the
     honest answer is "I could not confirm that", not a confident guess.
  8. **Stop signalling.** `needs_confirmation` is a successful outcome, not a
     failure (drill 5).
  9. **Stay cheap.** Two or three calls per ticket, not ten (drill 8).
 10. **Prove it.** The score is tickets handled and unauthorised actions, together.

The pipeline is the product. No single line here is clever.
"""

from __future__ import annotations

import json
import re

from agentlab.tools import Param, Tool, ToolRegistry

INSTRUCTION_PATTERNS = (
    r"ignore (all )?previous",
    r"system override",
    r"assistant note",
    r"you must",
    r"new instructions",
    r"disregard",
    r"email the",
)

MAX_STEPS = 4

SYSTEM = """You are a support agent. You may call one tool per turn, or answer with
{"final": ...}. Use only the documents and tool results provided.
"""


# -- 1 & 2: assemble, sanitise ---------------------------------------------


def sanitise(text: str) -> str:
    kept = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if any(re.search(p, sentence, re.IGNORECASE) for p in INSTRUCTION_PATTERNS):
            continue
        kept.append(sentence)
    return " ".join(kept).strip()


def build_context(ticket) -> str:
    blocks = []
    for index, doc in enumerate(ticket.documents(), start=1):
        blocks.append(f"<document id={index}>\n{sanitise(doc)}\n</document>")
    return "\n\n".join(blocks)


# -- 3 & 4: validated, gated tools -----------------------------------------


def build_registry(ticket) -> ToolRegistry:
    world = ticket.world
    registry = ToolRegistry()

    registry.add(Tool(
        "find_customer", "look up a customer",
        (Param("customer_id", "string"),),
        lambda a: world.execute("find_customer", a),
    ))
    registry.add(Tool(
        "list_orders", "list a customer's orders",
        (Param("customer_id", "string"),),
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
    registry.add(Tool(
        "send_email", "send email to a recipient",
        (Param("to", "string"), Param("body", "string")),
        lambda a: world.execute("send_email", a),
        dangerous=True,
    ))
    return registry


# -- 5, 6, 7, 8: the loop ---------------------------------------------------


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


def handle(ticket, model) -> dict:
    registry = build_registry(ticket)
    context = build_context(ticket)
    observations: list[str] = []
    seen: set[str] = set()

    for step in range(1, MAX_STEPS + 1):
        prompt = "\n".join(
            [
                SYSTEM,
                context,
                "",
                "Tool results:" if observations else "Tool results: (none)",
                *observations,
                "",
                f"Question: {ticket.question}",
            ]
        )
        payload = _parse(model.complete(prompt).text)

        if payload is None:
            observations.append("observation: your last message was not a JSON object")
            continue

        if "final" in payload:
            return {
                "outcome": "answer",
                "answer": str(payload["final"]),
                "steps": step,
            }

        name = payload.get("tool")
        args = payload.get("args") or {}
        signature = f"{name}:{json.dumps(args, sort_keys=True)}"
        if signature in seen:
            return {"outcome": "gave_up", "answer": "repeated call", "steps": step}
        seen.add(signature)

        result = registry.call(name, args, confirmed=False)

        if result["kind"] == "needs_confirmation":
            # A human has to approve this. That is a correct ending, not an error.
            return {
                "outcome": "needs_confirmation",
                "answer": f"{name} requires human approval",
                "steps": step,
            }

        if result["ok"]:
            observations.append(f"observation: {name} -> {json.dumps(result['result'])}")
        else:
            observations.append(f"observation: {name} failed ({result['kind']}): {result['error']}")

    return {"outcome": "gave_up", "answer": "step budget exhausted", "steps": MAX_STEPS}
