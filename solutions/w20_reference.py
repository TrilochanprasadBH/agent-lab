"""Reference solution for the debugging drill: the first stage where the evidence disappears.

This is the whole method, and it is deliberately mechanical:

    does the index contain the value at all?        no -> ingestion
    does any single chunk contain it whole?         no -> chunking
    was the chunk retrieved?                        no -> query, or retrieval
    was the chunk packed into the prompt?           no -> packing
    is the value in the answer?                     no -> stale, or generation

The order is the skill. Each check is cheap, each one eliminates every stage downstream of it,
and stopping at the first "no" is what makes the diagnosis a cause instead of a symptom.

Two checks need care:

**`query` before `retrieval`.** Both mean "the chunk was not retrieved". The difference is
whether the rewrite still contains the term that disambiguates the question. If it does, the
retriever failed; if it does not, the retriever was asked the wrong question.

**`stale` before `generation`.** Both mean "the value never reached the answer". Stale means the
prompt carried an older, superseded value that outvoted the current one. That is a different
repair: telling the model to ground itself will simply ground it in the wrong chunk.

`contains` is a whole-token match throughout. Substring matching turns `8 seconds` into a match
for `18 seconds`, and a debugging tool that reports false positives is worse than no tool.
"""

from __future__ import annotations

from drills.w20_debug.data import K, contains


def diagnose(case, model) -> dict:
    gold = case.gold

    if not contains("".join(chunk.text for chunk in case.index), gold):
        return {"stage": "ingestion", "fix": "reingest"}

    holders = [chunk for chunk in case.index if chunk.value == gold]
    if not holders:
        return {"stage": "chunking", "fix": "rechunk"}

    holder = holders[0]

    if holder.id not in case.retrieved:
        if not contains(case.rewritten, case.key_term):
            return {"stage": "query", "fix": "rewrite"}
        rank = case.gold_rank or len(case.ranking) + 1
        return {"stage": "retrieval", "fix": "raise_k" if rank <= K + 3 else "hybrid"}

    if holder.id not in case.prompt_chunks:
        return {"stage": "packing", "fix": "repack"}

    if not contains(case.answer, gold):
        if any(
            chunk.superseded and chunk.value and contains(case.answer, chunk.value)
            for chunk in case.index
        ):
            return {"stage": "stale", "fix": "supersede"}
        return {"stage": "generation", "fix": "ground"}

    return {"stage": "pass", "fix": "none"}
