# Drill 15 — regression gating

**Target:** 90% correct ship / block decisions.

```
python3 run.py --drill w15_regression
```

The rule:

```
ship   if aggregate improves by at least 2 points
       AND no slice regresses by 2 points or more
block  otherwise
```

## Simpson's paradox, with a deploy button

Twelve of these pull requests improve the aggregate **and** make one category
worse. A gate that looks only at the average ships all twelve.

The arithmetic is honest: one slice improves by 25%, another regresses by 12%, and
25 > 12, so the average goes up. The customers in the regressed slice experience a
12% worse product and no part of the average notices them.

## Why this is the highest-consequence drill here

Every other drill fails in the lab. This one describes the most common way a
production AI system degrades: not a dramatic break, but a sequence of releases
that each improved the number that was being watched.

An aggregate is a summary, and summaries hide distributions.

## The two rules

1. **Never gate on a single number.** Gate on the aggregate *and* the worst slice.
   The worst slice is where the incident comes from.
2. **Make the asymmetry explicit.** A false ship reaches users. A false block costs
   an engineer an hour. Set the thresholds so that asymmetry lives in the code,
   not in a review comment that nobody reads six months later.

## Done looks like

- [ ] TARGET MET with zero false ships
- [ ] your threshold constants are named and explained
- [ ] you check every slice, not the slices you remember
- [ ] you can explain to a product manager why a "plus 6%" release was blocked

## The question to take to work

What is the worst slice in your current eval, and how would you know if it moved?
If the answer is "we do not track slices", that is the finding — and it is worth
more than any number this drill produces.
