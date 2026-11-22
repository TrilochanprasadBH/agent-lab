"""Drill 13 — designing an eval set.

THIS IS THE FILE YOU EDIT.

Target: 90% on the two metrics — cell coverage and no duplicate sources.

You are given a pool of 240 candidate items. Select exactly 32 and return the list
of item ids.

Read `data.py`. Each item has a `tag`, a `difficulty` and a `source`. The score
asks two questions:

  - does your selection contain at least 2 items for every (tag, difficulty) cell?
  - did you avoid selecting two items from the same source document?

The baseline takes the first 32 items from the pool. The pool is sorted by tag.
"""

from __future__ import annotations

from .data import POOL

SELECT = 32


def select(run, model) -> list[str]:
    return [item.doc_id for item in POOL[:SELECT]]
