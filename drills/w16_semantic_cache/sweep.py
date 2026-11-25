#!/usr/bin/env python3
"""Print the threshold sweep quoted in `spec.md`.

    python3 drills/w16_semantic_cache/sweep.py

Every number in the drill's background section comes from this script. If the generator or the
scoring changes, the table changes, and the spec has to be edited to match — which is the point
of keeping the command next to the claim.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from drills.w16_semantic_cache import data  # noqa: E402

THRESHOLDS = (0.80, 0.88, 0.90, 0.94)


def main() -> int:
    days = data.build()
    turns = sum(len(day.turns) for day in days)

    print()
    print(f" {turns} turns across {len(days)} days, {data.INTENTS} intents")
    print(f" wrong-hit budget {data.WRONG_HIT_BUDGET:.0%}")
    print()
    print(" threshold   hit rate   wrong hits   cost")
    for threshold in THRESHOLDS:
        hits = wrong = calls = 0
        for day in days:
            cache: list = []
            for turn in day.turns:
                best = None
                best_score = -1.0
                for cached in cache:
                    score = data.cosine(turn.embedding, cached.embedding)
                    if score > best_score:
                        best, best_score = cached, score
                if best is not None and best_score >= threshold:
                    if data.TRUTH[best.id] == data.TRUTH[turn.id]:
                        hits += 1
                    else:
                        wrong += 1
                else:
                    calls += 1
                    cache.append(turn)
        print(
            f"   {threshold:.2f}      {hits / turns:5.1%}      {wrong / turns:5.1%}"
            f"      ${calls * 0.0004:.3f}"
        )
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
