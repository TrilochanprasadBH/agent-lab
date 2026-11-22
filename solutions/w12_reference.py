"""Reference solution for drill 12 — read this after trying your own.

Two questions, in this order. The order matters more than the statistics.

**First: are these runs even comparable?** If `a` and `b` were evaluated on
different items, no test can rescue the comparison. A difference in averages is a
difference in *question difficulty* at least as much as a difference in system
quality. The only correct action is to re-run on a shared set. This single check
accounts for most of the gap in this drill.

**Second: are the runs paired?** If they share items, you are not comparing two
samples of 48 — you are looking at 48 *pairs*. A pair where both pass, or both
fail, tells you nothing about which system is better. Only the discordant pairs
carry information:

    n01  A passed, B failed   (B got worse)
    n10  A failed, B passed   (B got better)

Under the null hypothesis, a discordant pair is a coin flip. So test n10 against
Binomial(n01 + n10, 0.5). That is McNemar's test, and it is the right test for
paired pass/fail data — no normality assumption, no variance estimate, and far
more powerful than comparing means.

A paired design on 48 items detects changes that an unpaired comparison on the
same 48 items cannot see, because pairing removes item difficulty from the
variance. That is the whole trick.
"""

from __future__ import annotations

import math

ALPHA = 0.05
MIN_EFFECT = 0.02


def _binom_two_sided(k: int, n: int) -> float:
    """Exact two-sided binomial p-value for k successes out of n at p=0.5."""
    if n == 0:
        return 1.0
    total = 0.0
    for i in range(n + 1):
        prob = math.comb(n, i) / (2 ** n)
        if prob <= (math.comb(n, k) / (2 ** n)) + 1e-12:
            total += prob
    return min(1.0, total)


def decide(run, model) -> dict:
    # 1. Comparable? Same items or nothing.
    if set(run.a) != set(run.b):
        return {"ship": False, "reason": "runs used different item sets"}

    n01 = sum(1 for item in run.a if run.a[item] and not run.b[item])
    n10 = sum(1 for item in run.a if run.b[item] and not run.a[item])
    n = len(run.a)

    # 2. Is the effect big enough to be worth shipping at all?
    effect = (n10 - n01) / n
    if effect < MIN_EFFECT:
        return {"ship": False, "reason": "effect too small to matter"}

    # 3. Is it distinguishable from a coin flip?
    p_value = _binom_two_sided(n10, n01 + n10)
    return {
        "ship": p_value < ALPHA and n10 > n01,
        "p_value": round(p_value, 4),
        "discordant": (n01, n10),
    }
