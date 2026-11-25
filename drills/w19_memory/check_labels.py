#!/usr/bin/env python3
"""Verify the labels and the structure the drill depends on.

    python3 drills/w19_memory/check_labels.py

The corpus is authored, because the exercise needs facts that are stated once, corrected twice,
and never repeated — no public conversation corpus carries those labels. Authored labels are
exactly the kind that drift silently, so every claim the lesson makes about the corpus is checked
here rather than asserted in prose.

1. every expected value appears in its own conversation
2. every stale value appears, and the naive extraction rule the probe declares is actually wrong
   on this transcript — `naive_fails` is "first", "last" or "both", so the correction is a real
   trap and not a value that happens to be the only mention
3. the model's decoy pool for each probe never contains the right answer, so a confabulated
   value can never be scored correct
4. the conversation is at least three times the memory budget
5. the truncation baseline keeps the `late` and `unstructured` probes and loses every `early`,
   `constraint` and `corrected` one — which is why it scores 30.8% and not more
6. the reference ledger contains every expected value except the one that is not a fact
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from drills.w19_memory import data  # noqa: E402
from drills.w19_memory.data import BUDGET_TOKENS, count_tokens, _contains, _norm  # noqa: E402
from solutions.w19_reference import ledger  # noqa: E402


def baseline_window(conversation) -> str:
    kept: list[str] = []
    used = 0
    for turn in reversed(conversation.turns):
        cost = count_tokens(turn)
        if used + cost > BUDGET_TOKENS:
            break
        kept.append(turn)
        used += cost
    return "\n".join(reversed(kept))


def mentions(transcript: str, phrases: tuple[str, ...]) -> list[tuple[int, str]]:
    """Every occurrence of every phrase, in reading order, as (position, phrase)."""
    found: list[tuple[int, str]] = []
    haystack = transcript.casefold()
    for phrase in phrases:
        pattern = r"(?<!\w)" + re.escape(_norm(phrase)) + r"(?!\w)"
        for match in re.finditer(pattern, haystack):
            found.append((match.start(), phrase))
    return sorted(found)


def main() -> int:
    conversations = data.build()
    model = data.model(conversations)
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    for conversation in conversations:
        haystack = _norm(conversation.transcript)
        window = _norm(baseline_window(conversation))

        check(
            count_tokens(conversation.transcript) >= 3 * BUDGET_TOKENS,
            f"{conversation.id}: transcript is only "
            f"{count_tokens(conversation.transcript)} tokens, less than 3x the budget",
        )

        for probe in conversation.probes:
            check(
                any(_contains(haystack, phrase) for phrase in probe.accept),
                f"{probe.id}: expected value {probe.accept[0]!r} is not in the transcript",
            )

            if probe.stale:
                order = mentions(conversation.transcript, probe.accept + probe.stale)
                check(bool(order), f"{probe.id}: no mention of either value")
                if order:
                    first, last = order[0][1], order[-1][1]
                    if probe.naive_fails in ("first", "both"):
                        check(
                            first in probe.stale,
                            f"{probe.id}: first mention is already the new value, so "
                            "'take the first match' is not wrong",
                        )
                    if probe.naive_fails in ("last", "both"):
                        check(
                            last in probe.stale,
                            f"{probe.id}: last mention is already the new value, so "
                            "'take the last match' is not wrong",
                        )
                    check(
                        bool(probe.naive_fails),
                        f"{probe.id}: has a stale value but declares no naive rule that fails",
                    )

            for decoy in model.decoys_for(probe):
                check(
                    not any(_contains(_norm(decoy), phrase) for phrase in probe.accept),
                    f"{probe.id}: decoy {decoy!r} contains the expected value, so a "
                    "confabulated answer could be scored correct",
                )

            if probe.category in ("late", "unstructured"):
                check(
                    any(_contains(window, phrase) for phrase in probe.accept),
                    f"{probe.id}: the truncation baseline should keep this "
                    f"{probe.category} probe, but {probe.accept[0]!r} is outside the window",
                )
            else:
                check(
                    not any(_contains(window, phrase) for phrase in probe.accept),
                    f"{probe.id}: the truncation baseline should lose this "
                    f"{probe.category} probe, but {probe.accept[0]!r} is inside the window",
                )

        memory = _norm(ledger(conversation.transcript))
        for probe in conversation.probes:
            if probe.category == "unstructured":
                continue
            check(
                any(_contains(memory, phrase) for phrase in probe.accept),
                f"{probe.id}: the reference ledger is missing {probe.accept[0]!r}",
            )

    if failures:
        print(f" {len(failures)} problem(s)")
        for failure in failures:
            print(f" - {failure}")
        return 1

    probes = sum(len(c.probes) for c in conversations)
    categories = sorted({p.category for c in conversations for p in c.probes})
    kept = sum(
        1 for c in conversations for p in c.probes if p.category in ("late", "unstructured")
    )
    print(f" ok: {len(conversations)} conversations, {probes} probes, categories {categories}")
    print(f" truncation baseline keeps {kept} of {probes} probes = {kept / probes:.1%}")
    print(f" traps: {sum(1 for c in conversations for p in c.probes if p.naive_fails)} corrections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
