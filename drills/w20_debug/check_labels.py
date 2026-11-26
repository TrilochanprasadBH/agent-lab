#!/usr/bin/env python3
"""Verify that every case really contains the fault it claims.

    python3 drills/w20_debug/check_labels.py

Twelve of the fourteen checks below are about the corpus rather than about the reference: if the
gold leaked into the prompt of a `retrieval` case, or the prompt happened to be over budget in
every `packing` case, the lesson would be measuring the wrong thing and the numbers would still
look fine. The last two compare the declared label with what the reference solution concludes, so
a change to the corpus that silently reclassifies a case fails here rather than in a report.

1. every gold value appears in the corpus and is unique across it
2. ingestion: the value is in no chunk at all, and its document is absent from the index
3. chunking: the value survives concatenation but no single chunk contains it whole
4. query: the chunk was not retrieved, and the rewrite dropped the disambiguating term
5. retrieval: the chunk was not retrieved, and the rewrite kept the term
6. packing: the chunk was retrieved and left out of the prompt
7. generation: the chunk reached the prompt, the answer lacks the value, and no superseded value
   is in the answer
8. stale: the chunk reached the prompt, the answer lacks the value, and a superseded value is in
   the answer
9. retrieval repairs are unambiguous: the rank is either within three of the cut or at least 15
10. every (stage, fix) pair is one the drill documents
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from drills.w20_debug import data  # noqa: E402
from drills.w20_debug.data import K, STAGES, contains  # noqa: E402
from solutions.w20_reference import diagnose  # noqa: E402


def main() -> int:
    cases = data.build()
    problems: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            problems.append(message)

    corpus_text = "\n".join(
        f"The {param} for {doc.system} is {doc.values[param]}." for doc in data.DOCS for param in data.PARAMS
    )
    unique = {doc.values[param] for doc in data.DOCS for param in data.PARAMS}
    check(
        len(unique) == len(data.DOCS) * len(data.PARAMS),
        f"the corpus has {len(unique)} distinct values for "
        f"{len(data.DOCS) * len(data.PARAMS)} sections; a gold match would be ambiguous",
    )

    for case in cases:
        check(
            contains(corpus_text, case.gold),
            f"{case.id}: gold {case.gold!r} is not in the corpus",
        )
        joined = "".join(chunk.text for chunk in case.index)
        holder = case.gold_chunk
        retrieved = case.retrieved

        if case.stage == "ingestion":
            check(
                not contains(joined, case.gold),
                f"{case.id}: ingestion case still contains the gold in the index",
            )
            check(
                not any(chunk.value == case.gold for chunk in case.index),
                f"{case.id}: ingestion case still has the gold chunk",
            )
        elif case.stage == "chunking":
            check(
                contains(joined, case.gold),
                f"{case.id}: chunking case lost the gold entirely, which is ingestion",
            )
            check(holder is None, f"{case.id}: chunking case still has a whole gold chunk")
        elif case.stage == "query":
            check(holder is not None, f"{case.id}: query case has no gold chunk")
            check(holder not in retrieved, f"{case.id}: query case retrieved the gold")
            check(
                not contains(case.rewritten, case.key_term),
                f"{case.id}: the rewrite kept {case.key_term!r}, so this is not a query fault",
            )
        elif case.stage == "retrieval":
            check(holder is not None, f"{case.id}: retrieval case has no gold chunk")
            check(holder not in retrieved, f"{case.id}: retrieval case retrieved the gold")
            check(
                contains(case.rewritten, case.key_term),
                f"{case.id}: the rewrite dropped {case.key_term!r}, so this is a query fault",
            )
            rank = case.gold_rank or 0
            check(
                rank <= K + 3 or rank >= 15,
                f"{case.id}: rank {rank} is ambiguous between raise_k and hybrid",
            )
        elif case.stage == "packing":
            check(holder in retrieved, f"{case.id}: packing case did not retrieve the gold")
            check(
                holder not in case.prompt_chunks,
                f"{case.id}: packing case packed the gold anyway",
            )
        elif case.stage == "generation":
            check(holder in retrieved, f"{case.id}: generation case did not retrieve the gold")
            check(holder in case.prompt_chunks, f"{case.id}: generation case did not pack the gold")
            check(not contains(case.answer, case.gold), f"{case.id}: the answer contains the gold")
            check(
                not any(
                    chunk.superseded and chunk.value and contains(case.answer, chunk.value)
                    for chunk in case.index
                ),
                f"{case.id}: a superseded value is in the answer, so this is stale",
            )
        elif case.stage == "stale":
            check(holder in retrieved, f"{case.id}: stale case did not retrieve the gold")
            check(holder in case.prompt_chunks, f"{case.id}: stale case did not pack the gold")
            check(not contains(case.answer, case.gold), f"{case.id}: the answer contains the gold")
            check(
                any(
                    chunk.superseded and chunk.value and contains(case.answer, chunk.value)
                    for chunk in case.index
                ),
                f"{case.id}: no superseded value is in the answer, so this is generation",
            )

        documented = case.fix in (data.FIXES[case.stage], data.HYBRID)
        check(documented, f"{case.id}: fix {case.fix!r} is not documented for {case.stage}")

        verdict = diagnose(case, data.model())
        check(
            verdict["stage"] == case.stage and verdict["fix"] == case.fix,
            f"{case.id}: declared {case.stage}/{case.fix}, reference says "
            f"{verdict['stage']}/{verdict['fix']}",
        )

    counts = Counter(case.stage for case in cases)
    check(
        all(counts[stage] == len(cases) // len(STAGES) for stage in STAGES),
        f"classes are not balanced: {dict(counts)}",
    )
    check(len(cases) == len(data.build()), "build is not deterministic")

    if problems:
        print(f" {len(problems)} problem(s)")
        for problem in problems:
            print(f" - {problem}")
        return 1

    print(f" ok: {len(cases)} cases, {len(STAGES)} stages, {len(cases) // len(STAGES)} each")
    print(f" gold values unique across {len(data.DOCS)} documents x {len(data.PARAMS)} sections")
    print(
        " retrieval repairs: "
        f"{sum(1 for c in cases if c.fix == 'raise_k')} raise_k, "
        f"{sum(1 for c in cases if c.fix == 'hybrid')} hybrid"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
