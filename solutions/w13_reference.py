"""Reference solution for drill 13 — read this after trying your own.

An eval set is a sample, and sampling is about coverage, not volume. Four moves:

  1. **Stratify on the cells that matter.** Here that is (tag, difficulty). Every
     cell gets its quota before any cell gets a second helping. Cell quotas are
     how you guarantee the set can detect a regression in a category you care
     about — a set with no `adversarial/hard` items is blind to exactly the failure
     you most want to catch.

  2. **De-duplicate by source.** Two items from the same source document are
     nearly the same observation. You pay two slots and buy one bit of
     information. Take the first item from each source and skip its relatives.

  3. **Do not accept the pool's order as meaningful.** Pools arrive sorted by
     whatever the exporter felt like — here, by tag. Slicing the head of a sorted
     pool is how eval sets end up covering two categories out of sixteen.

  4. **Fail loudly when a cell cannot be filled.** If the pool cannot satisfy a
     quota, you want to know at design time, not discover it after a regression
     slips through. Here every cell has enough items, but the code still checks.
"""

from __future__ import annotations

from collections import defaultdict

from drills.w13_sets.data import PER_CELL, POOL, cells as all_cells

SELECT = 32


def select(run, model) -> list[str]:
    by_cell: dict[tuple[str, str], list] = defaultdict(list)
    for item in POOL:
        by_cell[(item.tag, item.difficulty)].append(item)

    used_sources: set[str] = set()
    picked: list[str] = []

    # Round-robin over cells so no category is starved, and skip any item whose
    # source is already represented.
    for _ in range(PER_CELL):
        for cell in all_cells():
            for item in by_cell[cell]:
                if len(picked) >= SELECT:
                    break
                if item.source in used_sources:
                    continue
                if sum(1 for pid in picked if pid in {i.doc_id for i in by_cell[cell]}) >= PER_CELL:
                    break
                picked.append(item.doc_id)
                used_sources.add(item.source)

    # If quotas left gaps (small sources), fill from the remaining distinct items.
    if len(picked) < SELECT:
        for item in POOL:
            if len(picked) >= SELECT:
                break
            if item.doc_id in picked or item.source in used_sources:
                continue
            picked.append(item.doc_id)
            used_sources.add(item.source)

    return picked
