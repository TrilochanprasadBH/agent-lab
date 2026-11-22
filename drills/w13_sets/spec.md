# Drill 13 — designing an eval set

**Target:** 90% on cell coverage and on no-duplicate-sources.

```
python3 run.py --drill w13_sets
```

Select 32 items from a pool of 240.

## An eval set is a sample, not a list

Two failure modes, and both are invisible until a regression slips through:

**Coverage.** The pool has 16 cells (8 tags × 2 difficulties). If your set has no
`adversarial/hard` items, your eval is structurally blind to exactly the failure
you most want to catch. A missing category is not a smaller eval; it is an eval
that answers a different question.

**Duplication.** Two items from the same source document are nearly the same
observation. You spend two slots and buy one bit of information. A 32-item set with
12 duplicate pairs is a 26-item set wearing a costume.

## The trap in the pool

The pool is sorted by tag. `POOL[:32]` looks harmless and covers two tags out of
eight — one tenth of the space, at full confidence.

This is what happens whenever an eval set is built by taking "the next N items" from
whatever the export produced. The order of an export is not a sampling strategy.

## The moves

1. **Stratify on the cells that matter**, and fill every cell's quota before any
   cell gets a second helping.
2. **De-duplicate by source**, preferring one item per source.
3. **Refuse the pool's order.** Sort, shuffle, or group — just do not slice.
4. **Check the quotas are satisfiable.** If a cell cannot be filled, that is a
   finding about your pool, and you want it at design time.

## Done looks like

- [ ] TARGET MET, both metrics
- [ ] every one of the 16 cells has at least 2 items
- [ ] no source appears twice
- [ ] you can name which cell you would add next and why

## Why this is the least glamorous, most valuable thing here

RAG bugs, agent bugs, and prompt bugs all get caught by the same instrument. When
that instrument cannot see a category, the category ships broken and nobody finds
out until a customer does.
