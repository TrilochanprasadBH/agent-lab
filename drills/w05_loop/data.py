"""Tasks that take several steps, and scripts that only become correct if you
feed the tool result back.

Each case is a conversation the model would have *if* something kept calling it.
That something is your loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class World:
    def __init__(self) -> None:
        self.customers = {
            "c100": {"customer_id": "c100", "name": "Aster Labs", "plan": "pro"},
            "c200": {"customer_id": "c200", "name": "Bellweather Co", "plan": "free"},
        }
        self.orders = {
            "o8712": {"order_id": "o8712", "customer_id": "c100", "status": "shipped", "amount": 120.5},
            "o8713": {"order_id": "o8713", "customer_id": "c100", "status": "pending", "amount": 62.0},
            "o9000": {"order_id": "o9000", "customer_id": "c200", "status": "refunded", "amount": 18.0},
        }
        self.log: list[dict] = []

    def find_customer(self, name: str) -> dict:
        for customer in self.customers.values():
            if customer["name"].casefold() == name.casefold():
                return dict(customer)
        raise KeyError(f"no customer named {name!r}")

    def list_orders(self, customer_id: str, status: str | None = None) -> list[dict]:
        rows = [o for o in self.orders.values() if o["customer_id"] == customer_id]
        if status:
            rows = [o for o in rows if o["status"] == status]
        return rows

    def get_order(self, order_id: str) -> dict:
        return dict(self.orders[order_id])

    def execute(self, name: str, args: dict) -> dict:
        fn = getattr(self, name, None)
        if fn is None or name.startswith("_"):
            raise KeyError(f"no tool {name!r}")
        self.log.append({"tool": name, "args": dict(args)})
        return fn(**args)


@dataclass
class Case:
    doc_id: str
    request: str
    script: list[str]
    expect_kind: str  # "answer" or "gave_up"
    expect_text: str
    max_steps: int = 5
    world: World = field(default_factory=World)
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.request)


def _call(tool: str, **args) -> str:
    import json

    return json.dumps({"tool": tool, "args": args})


def _final(text: str) -> str:
    import json

    return json.dumps({"final": text})


def build_cases() -> list[Case]:
    return [
        Case(
            "a01",
            "how many pending orders does Aster Labs have, and what is the order id",
            [
                _call("find_customer", name="Aster Labs"),
                _call("list_orders", customer_id="c100", status="pending"),
                _final("Aster Labs has 1 pending order: o8713"),
            ],
            "answer",
            "o8713",
        ),
        Case(
            "a02",
            "what is the status of order o8712",
            [
                _call("get_order", order_id="o8712"),
                _final("order o8712 is shipped"),
            ],
            "answer",
            "shipped",
        ),
        Case(
            "a03",
            "how many orders does Bellweather Co have in total",
            [
                _call("find_customer", name="Bellweather Co"),
                _call("list_orders", customer_id="c200"),
                _final("Bellweather Co has 1 order"),
            ],
            "answer",
            "1 order",
        ),
        Case(
            "a04",
            "the first tool call is malformed; recover and report order o8712",
            [
                _call("get_order"),
                _call("get_order", order_id="o8712"),
                _final("o8712 is shipped"),
            ],
            "answer",
            "shipped",
        ),
        Case(
            "a05",
            "the model invented a tool name; recover and find Aster Labs",
            [
                _call("find_customers", name="Aster Labs"),
                _call("find_customer", name="Aster Labs"),
                _final("Aster Labs is on the pro plan"),
            ],
            "answer",
            "pro",
        ),
        Case(
            "a06",
            "a lookup for a customer that does not exist",
            [
                _call("find_customer", name="Nobody Inc"),
                _final("no customer named Nobody Inc"),
            ],
            "answer",
            "nobody",
        ),
        Case(
            "a07",
            "the model gets stuck repeating the same call forever",
            [
                _call("get_order", order_id="o8712"),
            ]
            * 6,
            "gave_up",
            "",
            max_steps=5,
        ),
        Case(
            "a08",
            "the model keeps asking for a tool that errors",
            [
                _call("get_order", order_id="nope"),
            ]
            * 6,
            "gave_up",
            "",
            max_steps=5,
        ),
        Case(
            "a09",
            "two orders, report both ids",
            [
                _call("list_orders", customer_id="c100"),
                _final("o8712 and o8713"),
            ],
            "answer",
            "o8712",
        ),
        Case(
            "a10",
            "the model answers without ever calling a tool",
            [
                _final("the answer is 42"),
            ],
            "answer",
            "42",
            max_steps=3,
        ),
    ]


def corpus() -> list[Case]:
    return build_cases()
