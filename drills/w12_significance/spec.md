# Drill 12 — is the difference real?

**Target:** 90% correct ship / no-ship decisions, 35 run pairs.

```
python3 run.py --drill w12_significance
```

## Three kinds of comparison

| kind | what it looks like | what you may conclude |
|---|---|---|
| paired, real | same items, B fixes some of A's failures | B is better |
| paired, null | same items, differences are noise | nothing happened |
| **disjoint** | B was evaluated on a *different* item set | **nothing at all** |

The third is the one that burns people. The arithmetic is valid — B's average really
is higher — and the conclusion is worthless, because B's question set was easier.

**First check in any comparison: are the item ids the same?** If not, re-run. No
statistical technique recovers a comparison between different exams.

## Why pairing matters

Two runs on the same 96 items are not two samples. They are 96 *pairs*. Items where
both pass and both fail tell you nothing about which system is better. Only
discordant pairs carry information:

```
n01   A passed, B failed   → B got worse here
n10   A failed, B passed   → B got better here
```

Under the null, each discordant pair is a coin flip, so test `n10` against
Binomial(n01 + n10, 0.5). That is McNemar's test: exact, no normality assumption,
far more powerful than comparing means.

Pairing removes item difficulty from the variance. That is the entire trick, and
it is why a 96-item paired eval can detect a change that a 96-item unpaired
comparison cannot see.

## Done looks like

- [ ] TARGET MET
- [ ] your first line of code checks the item sets match
- [ ] you do not ship a 2-point difference on 48 items without a p-value
- [ ] you can explain why `n01` and `n10` are the only interesting counts

## The habit

"We improved the eval score" is not a finding. It is a claim that needs a
denominator, a sample size, and a comparison design. The people who get trusted
with eval infrastructure are the ones who can say "this is noise" without flinching.
