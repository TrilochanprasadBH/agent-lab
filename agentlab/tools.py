"""A tiny schema-validated tool registry.

Tool calls arrive from a language model as *text* and are, in practice, wrong
several percent of the time: missing parameters, numbers as strings, invented
enum values, arguments smuggled inside a JSON string, or a call to something
that does not exist. Most of the engineering in a tool-using agent lives right
here, and almost none of it is about the model.

The registry never raises. Every failure is returned as data, because that is
what an agent loop has to reason about:

    {"ok": False, "kind": "missing_param", "error": "refund requires order_id"}

Design choices worth copying:

  - validation happens *before* the handler runs, so a bad call cannot mutate
    state;
  - dangerous tools refuse to run without an explicit confirmation, so a model
    cannot authorize a destructive action by asserting that it is allowed;
  - type coercion is narrow and deliberate: "3" is an integer, "true" is a
    boolean, "3.5" is not an integer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Param:
    name: str
    type: str = "string"  # string | integer | number | boolean
    required: bool = True
    enum: tuple[str, ...] = ()
    description: str = ""


@dataclass
class Tool:
    name: str
    description: str
    params: tuple[Param, ...]
    handler: Callable[[dict], Any]
    dangerous: bool = False

    def schema(self) -> str:
        parts = []
        for p in self.params:
            bits = p.type
            if p.enum:
                bits += "|".join(p.enum)
            suffix = "" if p.required else "?"
            parts.append(f"{p.name}:{bits}{suffix}")
        flag = "  [requires confirm=true]" if self.dangerous else ""
        return f"- {self.name}({', '.join(parts)}) — {self.description}{flag}"


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)
    calls: list[dict] = field(default_factory=list)
    blocked: list[dict] = field(default_factory=list)

    def add(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def schema_text(self) -> str:
        return "\n".join(tool.schema() for tool in self.tools.values())

    def names(self) -> list[str]:
        return list(self.tools)

    def reset(self) -> None:
        self.calls.clear()
        self.blocked.clear()

    @property
    def dangerous_calls(self) -> list[dict]:
        return [c for c in self.calls if c["dangerous"]]

    def call(
        self,
        name: Any,
        args: Any = None,
        *,
        confirmed: bool = False,
    ) -> dict:
        if not isinstance(name, str):
            return self._reject(name, "bad_tool_name", f"tool name must be a string, got {type(name).__name__}")

        tool = self.tools.get(name)
        if tool is None:
            return self._reject(name, "unknown_tool", f"no tool named {name!r}")

        if args is None:
            args = {}
        if not isinstance(args, dict):
            return self._reject(name, "bad_arguments", "arguments must be an object")

        cleaned, error = self._validate(tool, args)
        if error is not None:
            return self._reject(name, error["kind"], error["error"])

        if tool.dangerous and not (confirmed or cleaned.get("confirm") is True):
            self.blocked.append({"tool": name, "args": cleaned, "kind": "needs_confirmation"})
            return self._reject(
                name,
                "needs_confirmation",
                f"{name} changes state; it needs confirm=true from a human decision, "
                "not from the model",
            )

        self.calls.append({"tool": name, "args": cleaned, "dangerous": tool.dangerous})
        try:
            return {"ok": True, "kind": "ok", "result": tool.handler(cleaned)}
        except Exception as exc:  # noqa: BLE001 — tool errors are data too
            return {"ok": False, "kind": "tool_error", "error": f"{type(exc).__name__}: {exc}"}

    # -- internals --------------------------------------------------------

    def _reject(self, name: Any, kind: str, error: str) -> dict:
        self.blocked.append({"tool": name, "kind": kind, "error": error})
        return {"ok": False, "kind": kind, "error": error}

    def _validate(self, tool: Tool, args: dict) -> tuple[dict, dict | None]:
        cleaned: dict[str, Any] = {}

        for param in tool.params:
            if param.name not in args or args[param.name] is None:
                if param.required:
                    return {}, {
                        "kind": "missing_param",
                        "error": f"{tool.name} requires {param.name}",
                    }
                continue

            value, error = _coerce(args[param.name], param)
            if error:
                return {}, {"kind": "bad_type", "error": f"{tool.name}.{param.name} {error}"}
            if param.enum and value not in param.enum:
                return {}, {
                    "kind": "bad_enum",
                    "error": f"{tool.name}.{param.name} must be one of {param.enum}, got {value!r}",
                }
            cleaned[param.name] = value

        unknown = set(args) - {p.name for p in tool.params} - {"confirm"}
        if unknown:
            return {}, {
                "kind": "unknown_param",
                "error": f"{tool.name} has no parameter(s) {sorted(unknown)}",
            }

        return cleaned, None


def _coerce(value: Any, param: Param) -> tuple[Any, str | None]:
    if param.type == "string":
        if not isinstance(value, str):
            return None, "must be a string"
        return value.strip(), None

    if param.type == "integer":
        if isinstance(value, bool):
            return None, "must be an integer"
        if isinstance(value, int):
            return value, None
        if isinstance(value, float) and value.is_integer():
            return int(value), None
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value.strip()), None
        return None, "must be an integer"

    if param.type == "number":
        if isinstance(value, bool):
            return None, "must be a number"
        if isinstance(value, (int, float)):
            return float(value), None
        if isinstance(value, str):
            try:
                return float(value.strip()), None
            except ValueError:
                return None, "must be a number"
        return None, "must be a number"

    if param.type == "boolean":
        if isinstance(value, bool):
            return value, None
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            return value.strip().lower() == "true", None
        return None, "must be true or false"

    return None, f"unsupported type {param.type}"
