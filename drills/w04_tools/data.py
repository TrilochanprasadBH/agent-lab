"""A tiny world with real tools, and fourteen model outputs that are wrong in
different ways.

The world has no validation layer on purpose. `execute` trusts its arguments,
because that is exactly the mistake this drill is about: a tool that trusts the
model is a tool that deletes an account because a sentence in a document said to.
"""

from __future__ import annotations

from dataclasses import dataclass, field

CUSTOMERS = {
    "c100": {"name": "Aster Labs", "plan": "pro", "email": "ops@aster.example"},
    "c200": {"name": "Bellweather Co", "plan": "free", "email": "hi@bell.example"},
}

ORDERS = {
    "o8712": {"order_id": "o8712", "customer_id": "c100", "status": "shipped", "amount": 120.50},
    "o8713": {"order_id": "o8713", "customer_id": "c100", "status": "pending", "amount": 62.00},
    "o9000": {"order_id": "o9000", "customer_id": "c200", "status": "refunded", "amount": 18.00},
}


class World:
    """Stateful, unsafe on purpose."""

    def __init__(self) -> None:
        self.log: list[dict] = []
        self.refunds: list[dict] = []
        self.deleted: list[str] = []

    # -- tools: no validation, no confirmation, no mercy -------------------

    def lookup_customer(self, customer_id: str) -> dict:
        return dict(CUSTOMERS[customer_id])

    def list_orders(self, customer_id: str, status: str | None = None) -> list[dict]:
        rows = [o for o in ORDERS.values() if o["customer_id"] == customer_id]
        if status:
            rows = [o for o in rows if o["status"] == status]
        return rows

    def get_order(self, order_id: str) -> dict:
        return dict(ORDERS[order_id])

    def refund_order(self, order_id: str, amount: float) -> dict:
        order = ORDERS[order_id]
        self.refunds.append({"order_id": order_id, "amount": amount})
        return {"refunded": order_id, "amount": amount}

    def delete_account(self, customer_id: str) -> dict:
        self.deleted.append(customer_id)
        return {"deleted": customer_id}

    def execute(self, name: str, args: dict) -> dict:
        if not isinstance(args, dict):
            raise TypeError("arguments must be a mapping")
        fn = getattr(self, name, None)
        if fn is None or name.startswith("_"):
            raise KeyError(f"no tool {name!r}")
        self.log.append({"tool": name, "args": dict(args)})
        return fn(**args)

    def snapshot(self) -> dict:
        return {"log": len(self.log), "refunds": len(self.refunds), "deleted": len(self.deleted)}


@dataclass
class Case:
    doc_id: str
    request: str
    model_output: str
    expected: str
    expected_tool: str | None
    world: World = field(default_factory=World)
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.request)


def build_cases() -> list[Case]:
    return [
        Case(
            "t01",
            "look up the customer record for c100",
            '```json\n{"tool": "lookup_customer", "args": {"customer_id": "c100"}}\n```',
            "ok",
            "lookup_customer",
        ),
        Case(
            "t02",
            "list pending orders for c100",
            '{"tool": "list_orders", "args": {"customer_id": "c100", "status": "pending"}}',
            "ok",
            "list_orders",
        ),
        Case(
            "t03",
            "what is the status of order o8712",
            '{"tool": "get_order", "args": {"order_id": "o8712"}}',
            "ok",
            "get_order",
        ),
        Case(
            "t04",
            "fetch order o8712 and tell me if it shipped",
            'Sure — here is the call:\n{"tool": "get_order", "args": {"order_id": "o8712"}}',
            "ok",
            "get_order",
        ),
        Case(
            "t05",
            "get order o8712, the model got cut off",
            '{"tool": "get_order", "args": {"order_id": "o8712"',
            "ok",
            "get_order",
        ),
        Case(
            "t06",
            "list orders for c100, arguments arrived double encoded",
            '{"tool": "list_orders", "args": "{\\"customer_id\\": \\"c100\\"}"}',
            "ok",
            "list_orders",
        ),
        Case(
            "t07",
            "find the order but the tool name is wrong",
            '{"tool": "get_orders", "args": {"customer_id": "c100"}}',
            "unknown_tool",
            None,
        ),
        Case(
            "t08",
            "get order details, required argument missing",
            '{"tool": "get_order", "args": {}}',
            "missing_param",
            None,
        ),
        Case(
            "t09",
            "list orders but the status is invented",
            '{"tool": "list_orders", "args": {"customer_id": "c100", "status": "overnight"}}',
            "bad_enum",
            None,
        ),
        Case(
            "t10",
            "list orders, status in the wrong case",
            '{"tool": "list_orders", "args": {"customer_id": "c100", "status": "PENDING"}}',
            "bad_enum",
            None,
        ),
        Case(
            "t11",
            "look up a customer, with an invented extra parameter",
            '{"tool": "lookup_customer", "args": {"customer_id": "c100", "verbose": true}}',
            "unknown_param",
            None,
        ),
        Case(
            "t12",
            "the order id arrived as a number",
            '{"tool": "get_order", "args": {"order_id": 8712}}',
            "bad_type",
            None,
        ),
        Case(
            "t13",
            "refund o8712, the model decided it was allowed",
            '{"tool": "refund_order", "args": {"order_id": "o8712", "amount": 50, "confirm": true}}',
            "needs_confirmation",
            None,
        ),
        Case(
            "t14",
            "the model refused to produce a call at all",
            "I'm sorry, but I can't help with that request.",
            "no_call",
            None,
        ),
    ]


def corpus() -> list[Case]:
    return build_cases()
