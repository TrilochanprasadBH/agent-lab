#!/usr/bin/env python3
"""Agent Lab — run a drill and get one honest number.

    python3 run.py                          # score with the simulated model
    python3 run.py --failures 5             # inspect what broke
    python3 run.py --task solutions/w01_reference.py
    python3 run.py --trace results/w01.jsonl

    python3 run.py --provider openrouter --model <id> --limit 5   # real, cheap
    python3 run.py --provider openrouter --model <id>             # full run

Real calls need OPENROUTER_API_KEY in the environment. Responses are cached on
disk, so rerunning an unchanged attempt is free.
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
from agentlab.providers import ProviderError, make_provider  # noqa: E402


def load_task(spec: str | None, default_module: str) -> tuple[object, str]:
    if spec is None:
        module = importlib.import_module(default_module)
        return module.extract, default_module.replace(".", "/") + ".py"

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


def build_model(args, corpus):
    if args.provider == "sim":
        return make_provider("sim", corpus_texts=[inv.raw for inv in corpus], seed=args.seed)
    try:
        return make_provider(
            args.provider,
            model_id=args.model,
            temperature=args.temperature,
            use_cache=not args.no_cache,
        )
    except ProviderError as exc:
        raise SystemExit(f"\n {exc}\n") from None


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
    parser.add_argument("--limit", type=int, default=0, help="score only the first N documents")
    parser.add_argument("--trace", default=None, help="write every model call to a JSONL file")
    parser.add_argument("--provider", default="sim", help="sim (default) or openrouter")
    parser.add_argument("--model", default=None, help="model id for real providers")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--no-cache", action="store_true", help="bypass the response cache")
    parser.add_argument("--target", type=float, default=None, help="override target accuracy")
    parser.add_argument("--cap", type=float, default=None, help="override cost cap in USD")
    args = parser.parse_args(argv)

    drill = importlib.import_module(f"drills.{args.drill}.drill")
    corpus = drill.corpus()
    if args.limit:
        corpus = corpus[: args.limit]

    model = build_model(args, corpus)
    task, task_path = load_task(args.task, f"drills.{args.drill}.task")

    endpoint = getattr(model, "model_id", "simulated")
    print()
    print(f" {drill.NAME}")
    print(f" {drill.PREMISE}")
    print(f" task   {task_path}")
    print(f" model  {endpoint}   docs {len(corpus)}   seed {args.seed}")

    card, results = run_drill(
        corpus,
        task,
        model,
        target_accuracy=args.target if args.target is not None else drill.TARGET_ACCURACY,
        max_cost_usd=args.cap if args.cap is not None else drill.MAX_COST_USD,
    )

    print()
    print(card.render(title=f"scorecard \u00b7 {args.drill}"))

    hits = getattr(model, "cache_hits", 0)
    if hits:
        print(f" cache  {hits} of {model.n_calls} calls served from disk (free)")

    if args.trace:
        path = pathlib.Path(args.trace)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for call in model.calls:
                fh.write(json.dumps(call) + "\n")
        print(f" trace  written to {path} ({len(model.calls)} calls)")

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
