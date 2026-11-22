# Drill 12 — Deciding whether a change is real

| | |
| --- | --- |
| **Goal** | Decide, from two eval runs, whether a change should ship. |
| **Outcome** | A decision function that gets 90% of 35 comparisons right, including the ones where the numbers look better and nothing happened. |
| **Target** | 90% correct decisions. |
| **Time** | 75 to 90 minutes. |

---

## 1. Why this drill exists

Every week someone says "the eval score went up". Sometimes that means the system
improved. Often it means the sample changed, or the run was noisy, or the
comparison was never valid in the first place.

The ability to tell the difference is what makes an eval worth having. Without it,
you are deploying changes based on arithmetic that happens to move.

## 2. What you are given

- `data.py`: 35 comparisons. Each has two runs, `a` and `b`, mapping item id to
  pass or fail, and a hidden truth of `ship` or `no_ship`.
- Three kinds of comparison:

| kind | count | what it looks like | correct answer |
| --- | --- | --- | --- |
| paired, real | 15 | same items, B fixes some of A's failures | `ship` |
| paired, null | 10 | same items, differences are noise | `no_ship` |
| disjoint | 10 | B ran on a different, easier item set | `no_ship` |

- `task.py`: the file you edit. It compares the two averages and ships when B is
  higher.

## 3. How to run it

```sh
python3 run.py --drill w12_significance
python3 run.py --drill w12_significance --failures 10
python3 run.py --drill w12_significance --task solutions/w12_reference.py
```

## 4. Background: the idea from first principles

**What the numbers are.** Each run is a set of items with a pass or fail result.
Accuracy is the fraction that passed. That is all.

**Question 1: are the two runs comparable?**

Look at the item ids. If `a` and `b` have the same ids, they were evaluated on the
same items and can be compared directly.

If they have different ids, they are two different exams. B's average may be higher
simply because B's questions were easier. No statistical technique recovers a
comparison between different exams, because the difference in difficulty is not
measured.

The only correct action is to re-run both systems on the same items. In this drill,
a disjoint comparison is always `no_ship`.

This check is the single largest source of error in the drill, and it comes before
any statistics.

**Question 2: if the runs are paired, what does a difference mean?**

Two runs on the same items are not two samples of 96. They are 96 *pairs*.

Sort the pairs into four groups:

| a | b | meaning |
| --- | --- | --- |
| pass | pass | both right, no information about which is better |
| fail | fail | both wrong, no information |
| pass | fail | B got worse here |
| fail | pass | B got better here |

The first two groups cannot tell you anything, because both systems did the same
thing. Only the disagreements carry information.

Call the counts `n01` (A passed, B failed) and `n10` (A failed, B passed).

**Question 3: could this split be chance?**

Assume there is no real difference. Then each disagreement is equally likely to go
either way, like a coin flip. Under that assumption, `n10` is a draw from a binomial
distribution with `n01 + n10` trials and probability one half.

The p-value is the probability of seeing a split at least this lopsided under that
assumption. If it is small, the assumption is unlikely, and we say the difference is
real.

This is McNemar's test. It is exact, it makes no assumption about the shape of the
data, and it is much more sensitive than comparing two averages, because pairing
removes the difficulty of individual items from the comparison.

**Question 4: is it big enough to matter?**

Statistical significance and practical importance are different. A real improvement
of half a point is still not worth a deployment. Decide on a minimum effect size
before you look at the data, and require both conditions: p-value below your
threshold, and effect above your floor.

**Why the baseline fails.** Comparing averages ships on any positive difference,
including differences produced by noise and differences produced by a different
question set. It gets all the null cases wrong about half the time and all the
disjoint cases wrong.

## 5. The task, step by step

1. Run the starting code. Note the split between false ships and false blocks.
2. First, check that `set(a) == set(b)`. If not, return `no_ship`.
3. Count `n01` and `n10`.
4. Compute the effect size: `(n10 - n01) / n`.
5. If the effect is below your floor, return `no_ship`.
6. Compute the two-sided binomial p-value for `n10` out of `n01 + n10`.
7. Return ship only if the p-value is below 0.05 and `n10` exceeds `n01`.

## 6. How you are scored

`correct decisions` is the fraction of the 35 comparisons where your decision matches
the hidden truth. The drill passes at 90%.

The notes report false ships and false blocks separately. They are not equally
costly: a false ship reaches users, a false block costs an hour. Look at both.

A small number of false blocks is expected. Some real improvements in this dataset
are too small for 96 paired items to detect, and calling them "not proven" is the
correct behaviour even though the label says otherwise.

## 7. Done when

- [ ] `python3 run.py --drill w12_significance` reports TARGET MET
- [ ] your first line of code checks the item sets match
- [ ] you can explain why `n01` and `n10` are the only interesting counts
- [ ] you are not shipping 2-point differences on 96 items without a p-value
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

Four questions, in this order, before you say "it improved":

1. Were the runs on the same items?
2. How many pairs disagreed, and in which direction?
3. Could that split be chance?
4. Is the effect large enough to be worth shipping?

"We improved the eval score" is not a finding. It is a claim that needs a
comparison design, a sample size, and a decision rule.
