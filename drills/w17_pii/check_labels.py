#!/usr/bin/env python3
"""Verify the labels this drill depends on.

    python drills/w17_pii/check_labels.py

The corpus is authored, so the labels are the artefact and `AGENTS.md` requires them to be
verified rather than trusted. Six invariants:

  1. every span is inside its message, and its offsets cover a non-empty value
  2. spans in a message do not overlap
  3. every occurrence of a labelled value is labelled — not just the first one
  4. every span's category is in the taxonomy
  5. every message carries at least one span
  6. every category has at least five spans, so no metric rests on one example

Invariant 3 is the one that matters. A redactor is scored on spans, and a corpus where the
same address appears twice but is labelled once would teach the wrong lesson: perfect recall
against a corpus that is wrong.
"""

from __future__ import annotations

import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from drills.w17_pii import data  # noqa: E402


def main() -> int:
    messages = data.build()
    problems: list[str] = []
    categories: Counter[str] = Counter()

    for message in messages:
        if not message.spans:
            problems.append(f"{message.id}: no spans")

        ordered = sorted(message.spans, key=lambda span: span.start)
        previous = None
        for span in ordered:
            if span.category not in data.CATEGORIES:
                problems.append(f"{message.id}: unknown category {span.category!r}")
            if not 0 <= span.start < span.end <= len(message.text):
                problems.append(f"{message.id}: span out of bounds {span}")
                continue
            if previous is not None and span.start < previous.end:
                problems.append(f"{message.id}: overlapping spans at {span.start}")
            previous = span

            value = message.text[span.start : span.end]
            if not value.strip():
                problems.append(f"{message.id}: empty value at {span.start}")
            categories[span.category] += 1

            # Every occurrence of this value must be a span of the same category.
            start = message.text.find(value)
            occurrences = 0
            while start != -1:
                occurrences += 1
                covered = any(
                    other.start == start
                    and other.end == start + len(value)
                    and other.category == span.category
                    for other in message.spans
                )
                if not covered:
                    problems.append(
                        f"{message.id}: {value!r} at {start} is unlabelled"
                    )
                start = message.text.find(value, start + 1)
            if occurrences == 0:
                problems.append(f"{message.id}: span value vanished")

    for category in data.CATEGORIES:
        if categories[category] < 5:
            problems.append(f"{category}: only {categories[category]} spans, need 5")

    print()
    print(f" messages     {len(messages)}")
    print(f" spans        {sum(categories.values())}")
    print(f" categories   {len(categories)}")
    for category in data.CATEGORIES:
        print(f"   {category:<12} {categories[category]}")
    print(f" problems     {len(problems)}")
    for problem in problems[:20]:
        print(f"   {problem}")
    print()
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
