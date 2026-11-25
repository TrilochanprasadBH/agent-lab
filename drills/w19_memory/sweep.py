#!/usr/bin/env python3
"""Compare the four ways of carrying a long conversation into the next call.

    python3 drills/w19_memory/sweep.py

  truncate          keep the most recent turns that fit                      the default
  summary           summarise the older turns, keep the last six verbatim    one model call
  ledger            extract twelve facts, label them, drop the prose         no model call
  ledger + window   the ledger plus the last six turns for continuity        no model call

Every number in `spec.md` comes from here. The ledger row is the shipped reference solution, so
this table and `run.py --task solutions/w19_reference.py` cannot disagree.

The column to watch is `wrong`. An abstention is a system that knows it forgot; a wrong answer
is a system that does not. Truncation loses forty-six per cent of the probes and answers
twenty-nine per cent of them with a value the customer never gave.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentlab.drill import run_drill  # noqa: E402

from drills.w19_memory import data  # noqa: E402
from drills.w19_memory.data import BUDGET_TOKENS, RECENT_TURNS, count_tokens  # noqa: E402
from drills.w19_memory.drill import score  # noqa: E402
import re  # noqa: E402

from solutions.w19_reference import PATTERNS, _negated, ledger  # noqa: E402


def truncate(conversation, model):
    kept: list[str] = []
    used = 0
    for turn in reversed(conversation.turns):
        cost = count_tokens(turn)
        if used + cost > BUDGET_TOKENS:
            break
        kept.append(turn)
        used += cost
    memory = "\n".join(reversed(kept))
    return [model.answer(probe, memory) for probe in conversation.probes]


def recent_text(conversation) -> str:
    return "\n".join(conversation.turns[-RECENT_TURNS:])


def summarise(conversation, model):
    recent = recent_text(conversation)
    allowance = BUDGET_TOKENS - count_tokens(recent)
    older = "\n".join(conversation.turns[:-RECENT_TURNS])
    summary = model.summarise(older, max(20, allowance))
    memory = summary.text + "\n" + recent
    return [model.answer(probe, memory) for probe in conversation.probes]


def ledger_only(conversation, model):
    memory = ledger(conversation.transcript)
    return [model.answer(probe, memory) for probe in conversation.probes]


def ledger_and_window(conversation, model):
    memory = ledger(conversation.transcript) + "\n" + recent_text(conversation)
    return [model.answer(probe, memory) for probe in conversation.probes]


POLICIES = (
    ("truncate", truncate),
    ("summary", summarise),
    ("ledger", ledger_only),
    ("ledger + window", ledger_and_window),
)


def ledger_rule(rule: str):
    """Build a ledger using one naive rule, to price the correction handling on its own.

    `first` and `last` are what a reasonable person writes before thinking about corrections.
    `negated` is the reference: the last mention that is not preceded by `not`.
    """

    def build(transcript: str) -> str:
        lines = []
        for _, label, pattern in PATTERNS:
            matches = list(re.finditer(pattern, transcript))
            if not matches:
                continue
            if rule == "first":
                match = matches[0]
            elif rule == "last":
                match = matches[-1]
            else:
                kept = [m for m in matches if not _negated(transcript, m.start())]
                match = (kept or matches)[-1]
            lines.append(f"{label}: {match.group(1).strip()}")
        return "\n".join(lines)

    return build


def make_ledger_policy(build) -> object:
    def policy(conversation, model):
        memory = build(conversation.transcript) + "\n" + recent_text(conversation)
        return [model.answer(probe, memory) for probe in conversation.probes]

    return policy


def evaluate(policy):
    conversations = data.build()
    model = data.model(conversations)
    results = run_drill(conversations, policy, model)
    return score(results, model, 0.85, 0.020), model


def main() -> int:
    conversations = data.build()
    print()
    print(
        f" {len(conversations)} conversations, {len(conversations[0].probes)} probes each, "
        f"{count_tokens(conversations[0].transcript)} tokens each, "
        f"budget {BUDGET_TOKENS}"
    )
    print()
    header = (
        f" {'policy':<16}{'retained':>9}{'early':>7}{'constr':>8}{'corr':>7}{'late':>7}{'other':>7}"
        f"{'wrong':>7}{'abstain':>9}{'memory':>8}{'cost':>9}"
    )
    print(header)
    for name, policy in POLICIES:
        card, model = evaluate(policy)
        field = card.per_field
        print(
            f" {name:<16}{field['retained']:>9.1%}"
            f"{field['early']:>7.0%}"
            f"{field['constraint']:>8.0%}"
            f"{field['corrected']:>7.0%}"
            f"{field['late']:>7.0%}"
            f"{field['unstructured']:>7.0%}"
            f"{field['wrong answers']:>7.1%}"
            f"{field['abstained']:>9.1%}"
            f"{model.max_memory_tokens:>8}"
            f"${model.cost_usd:>8.4f}"
        )
    print()
    print(" columns: retained is the score; the next five are probe groups, `other` is the")
    print(" probe that no fact schema anticipates.")
    print(" memory is the largest memory sent to a single answer call, in tokens.")
    print()

    print(" correction handling, ledger + window, only the rule for picking a mention changes")
    print()
    print(f" {'rule':<14}{'retained':>9}{'corrected':>11}{'wrong':>7}")
    for rule, label in (
        ("first", "first match"),
        ("last", "last match"),
        ("negated", "skip negated"),
    ):
        card, _ = evaluate(make_ledger_policy(ledger_rule(rule)))
        print(
            f" {label:<14}{card.per_field['retained']:>9.1%}"
            f"{card.per_field['corrected']:>11.0%}"
            f"{card.per_field['wrong answers']:>7.1%}"
        )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
