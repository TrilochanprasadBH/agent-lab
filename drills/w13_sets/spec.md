# Drill 13 — Designing an eval set

| | |
| --- | --- |
| **Goal** | Choose a small sample of test items that covers everything you care about. |
| **Outcome** | A selection of 32 items, from a pool of 240, that covers all 16 categories and uses no source document twice. |
| **Target** | 90% on both coverage and duplication. |
| **Time** | 45 to 60 minutes. |

---

## 1. Why this drill exists

An eval measures what is in it. Nothing else.

If your test set has no questions about international orders, then international
orders can break, and your eval will report that nothing changed. A missing category
is not a smaller eval. It is an eval that answers a different question from the one
you think you are asking.

This drill is about sampling, which is the least glamorous and most consequential
part of evaluation.

## 2. What you are given

- `data.py`: a pool of 240 candidate items.
- Each item has three properties you can use:
  - `tag`: one of eight topics (refund, billing, retrieval, tools, auth,
    long-context, adversarial, multi-hop);
  - `difficulty`: easy or hard;
  - `source`: the document it was derived from. Several items can share a source.
- There are 16 categories in total: eight tags times two difficulties.
- `task.py`: the file you edit. It takes the first 32 items in the pool.

## 3. How to run it

```sh
python3 run.py --drill w13_sets
python3 run.py --drill w13_sets --failures 6
python3 run.py --drill w13_sets --task solutions/w13_reference.py
```

## 4. Background: the idea from first principles

**What a sample is.** You have a population of possible questions. You can only test
a few. The set you choose is a sample, and its quality is determined by what it
represents, not by how large it is.

**What coverage means here.** The score asks whether every one of the 16 categories
has at least two items. Two, not one, because a single item tells you about that item
and a pair tells you something about the category: if one of two questions breaks,
you can see whether the other held.

A set of 32 items spread evenly across 16 categories covers everything. A set of 32
items from two categories covers two sixteenths of the space, at full confidence.

**Why duplication is a waste.** If two items came from the same source document, they
ask nearly the same thing. You spend two slots and buy one piece of information. A
32-item set with twelve pairs from the same sources is effectively a 26-item set.

This matters more than it sounds: duplicate-heavy eval sets look large, run slowly,
and under-detect.

**Why the pool's order is a trap.** The pool is sorted by tag. Taking the first 32
items is not random, it is the first two tags. This is not a contrived trap. Exports
are sorted by whatever the exporter produced, and "take the first N" is the default
implementation of "pick some examples".

Order is not a sampling strategy.

**Stratified sampling.** The general technique:

1. Divide the population into groups that matter.
2. Decide how many items each group gets.
3. Fill each group's quota before giving any group extra.

This guarantees coverage by construction. It is the same idea as a stratified train
and test split, and the same idea as a per-category regression gate in drill 15.

## 5. The task, step by step

1. Run the starting code. Look at coverage: it will be near two sixteenths.
2. Group the pool by `(tag, difficulty)`.
3. Decide your quota: two items per category uses exactly 32 slots.
4. Fill quotas in a round-robin so no category is starved.
5. For each slot, pick an item whose `source` you have not used yet.
6. If a category cannot fill its quota with distinct sources, record that. It is a
   finding about the pool, not a failure of your sampler.
7. Return the list of item ids.

## 6. How you are scored

Two metrics.

`cell coverage` is the mean, over the 16 categories, of `min(count // 2, 1)`. A
category with two or more selected items scores 1. One item scores 0.5. None scores
0.

`no duplicate sources` is 1.0 minus the fraction of slots spent on a repeated source.

`accuracy` is the mean of the two. The drill passes at 90%.

## 7. Done when

- [ ] `python3 run.py --drill w13_sets` reports TARGET MET
- [ ] all 16 categories have at least two items
- [ ] no source appears twice
- [ ] you can name which category you would add items to next, and why
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

An eval set is a sample, and sampling is about coverage.

1. decide which categories matter before you pick anything
2. give every category a quota
3. de-duplicate by source
4. never treat the order of an export as random

If you remember one thing: a category your eval does not contain is a category your
eval cannot protect.
