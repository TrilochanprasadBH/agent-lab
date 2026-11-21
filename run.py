#!/usr/bin/env python3
"""Agent Lab — run a drill and get one honest number.

    python3 run.py                          # score the current drill
    python3 run.py --failures 5             # inspect what broke
    python3 run.py --task solutions/w01_reference.py
    python3 run.py --trace results/w01.jsonl

Nothing leaves your machine and no API key is needed.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agentlab.drill import run_drill  # noqa: E402


def load_task(spec: str | None) -> tuple[object, str]:
    if spec is None:
        module = importlib.import_module("drills.w01_extraction.task")
        return module.extract, "drills/w01_extraction/task.py"

    path_part, _, func_name = spec.partition(":")
    func_name = func_name or "extract"
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


def show_failures(results, card, limit: int) -> None:
    failures = [f for f in card.failures if f["cause"] != "missing / null"][:limit]
    if not failures:
        return
    print()
    print(f" first {len(failures)} failure(s)")
    for item in failures:
        doc = next(r.invoice for r in results if r.invoice.doc_id == item["doc_id"])
        print(" " + "-" * 60)
        print(f" {doc.doc_id}  field={item['field']}  ({item['cause']})")
        for line in doc.raw.splitlines()[:2]:
            print(f"   | {line}")
        print(f"   expected : {item['expected']!r}")
        print(f"   predicted: {item['predicted']!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run an Agent Lab drill.")
    parser.add_argument("--drill", default="w01_extraction")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--task", default=None, help="path/to/file.py[:function]")
    parser.add_argument("--failures", type=int, default=3)
    parser.add_argument("--trace", default=None, help="write every model call to a JSONL file")
    args = parser.parse_args(argv)

    drill = importlib.import_module(f"drills.{args.drill}.drill")
    corpus, model = drill.build(seed=args.seed)
    task, task_path = load_task(args.task)

    print()
    print(f" {drill.NAME}")
    print(f" {drill.PREMISE}")
    print(f" task  {task_path}   docs {len(corpus)}   seed {args.seed}")

    card, results = run_drill(
        corpus,
        task,
        model,
        target_accuracy=drill.TARGET_ACCURACY,
        max_cost_usd=drill.MAX_COST_USD,
    )

    print()
    print(card.render(title=f"scorecard \u00b7 {args.drill}"))

    if args.trace:
        path = pathlib.Path(args.trace)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for call in model.calls:
                fh.write(json.dumps(call) + "\n")
        print(f"\n trace written to {path} ({len(model.calls)} calls)")

    show_failures(results, card, args.failures)

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


if __name__ == "__main__":
    raise SystemExit(main())
