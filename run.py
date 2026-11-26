#!/usr/bin/env python3
"""Agent Lab — run a drill and get one honest number."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agentlab.drill import run_drill  # noqa: E402
from agentlab.evals import SCORED_FIELDS  # noqa: E402
from agentlab.providers import ProviderError  # noqa: E402


def load_task(spec: str | None, default_module: str, func_name: str = "extract") -> tuple[object, str]:
    if spec is None:
        module = importlib.import_module(default_module)
        return getattr(module, func_name), default_module.replace(".", "/") + ".py"

    path_part, _, explicit = spec.partition(":")
    func_name = explicit or func_name
    path = pathlib.Path(path_part)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise SystemExit(f"no such task file: {path}")

    module_name = f"_task_{path.stem}"
    module_spec = importlib.util.spec_from_file_location(module_name, path)
    if module_spec is None or module_spec.loader is None:
        raise SystemExit(f"cannot load {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)

    try:
        return getattr(module, func_name), str(path.relative_to(ROOT))
    except AttributeError:
        raise SystemExit(f"{path} has no function {func_name!r}()") from None


def build_model(args, drill):
    if args.provider == "sim":
        return drill.build_model(seed=args.seed)

    if not getattr(drill, "SUPPORTS_REAL", False):
        raise SystemExit(
            f"\n {args.drill} is a deterministic world; a real model would change the\n"
            " ground truth, not the lesson. Run it with the default --provider sim.\n"
        )

    from agentlab.providers import make_provider

    try:
        return make_provider(
            args.provider,
            model_id=args.model,
            temperature=args.temperature,
            use_cache=not args.no_cache,
        )
    except ProviderError as exc:
        raise SystemExit(f"\n {exc}\n") from None


def show_failures(card, limit: int) -> None:
    rows = [f for f in card.failures if f.get("cause") not in ("missing / null",)][:limit]
    if not rows:
        return
    print()
    print(f" first {len(rows)} failure(s)")
    for item in rows:
        mm = " " + "-" * 60
        print(mm)
        stem = item.get("doc_id", "?")
        field = item.get("field")
        label = f"{stem}  field={field}" if field else str(stem)
        print(f" {label}  ({item.get('cause', '')})")
        if item.get("detail"):
            print(f"   | {item['detail']}")
        if "expected" in item:
            print(f"   expected : {item['expected']!r}")
        if "predicted" in item:
            print(f"   predicted: {item['predicted']!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an Agent Lab drill.")
    parser.add_argument("--drill", default="w01_extraction")
    parser.add_argument("--list", action="store_true", help="list available drills")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--task", default=None, help="path/to/file.py[:function]")
    parser.add_argument("--failures", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0, help="score only the first N items")
    parser.add_argument("--trace", default=None, help="write every model call to a JSONL file")
    parser.add_argument("--provider", default="sim", help="sim (default) or openrouter")
    parser.add_argument("--model", default=None, help="model id for real providers")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--no-cache", action="store_true", help="bypass the response cache")
    parser.add_argument("--target", type=float, default=None, help="override target accuracy")
    parser.add_argument("--cap", type=float, default=None, help="override cost cap in USD")
    args = parser.parse_args(argv)

    if args.list:
        return list_drills()

    drill = importlib.import_module(f"drills.{args.drill}.drill")
    items = drill.corpus()
    if args.limit:
        items = items[: args.limit]

    model = build_model(args, drill)
    task, task_path = load_task(
        args.task,
        f"drills.{args.drill}.task",
        getattr(drill, "TASK_NAME", "extract"),
    )

    target = args.target if args.target is not None else drill.TARGET_ACCURACY
    cap = args.cap if args.cap is not None else drill.MAX_COST_USD

    endpoint = getattr(model, "model_id", getattr(model, "name", "simulated"))
    print()
    print(f" {drill.NAME}")
    print(f" {drill.PREMISE}")
    print(f" task   {task_path}")
    print(f" model  {endpoint}   items {len(items)}   seed {args.seed}")

    results = run_drill(items, task, model)
    card = drill.score(results, model, target, cap)

    print()
    print(card.render(title=f"scorecard \u00b7 {args.drill}"))

    if getattr(model, "cache_hits", 0):
        print(f" cache  {model.cache_hits} of {model.n_calls} calls served from disk (free)")

    if args.trace:
        import json

        path = pathlib.Path(args.trace)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for call in model.calls:
                fh.write(json.dumps(call) + "\n")
        print(f" trace  written to {path} ({len(model.calls)} calls)")

    show_failures(card, args.failures)

    hints = card.hints()
    if hints and not card.passed:
        print()
        print(" next move")
        for hint in hints[:3]:
            print(f" - {hint}")

    if card.passed:
        print("\n Target met. Change the seed, or write down what moved the number.")
    print()
    return 0


def list_drills() -> int:
    import pkgutil

    import drills

    print()
    for info in pkgutil.iter_modules(drills.__path__):
        if not info.ispkg:
            continue
        try:
            module = importlib.import_module(f"drills.{info.name}.drill")
        except Exception:  # noqa: BLE001
            continue
        print(f" {info.name:<22} {getattr(module, 'NAME', '')}")
        print(f" {'':<22} target {module.TARGET_ACCURACY:.0%}  cap ${module.MAX_COST_USD:g}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
