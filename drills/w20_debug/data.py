"""Forty-two failing RAG questions, and the seven places the evidence can die.

Every case is the same shape: a question, the query the retriever actually ran, the full
candidate ranking, the chunks that reached the prompt, and the answer that was sent. Every case
has a wrong answer. The job is to name the **first** stage where the evidence disappeared, because
that is the only stage whose repair changes anything downstream.

    index      the chunk is not in the index at all
    chunk      the text is in the index, but no chunk contains it whole
    query      the rewrite dropped the term that disambiguates the question
    retrieval  the chunk exists and the query was fine; the ranking put it too low
    packing    the chunk was retrieved and then left out of the prompt
    generation the chunk reached the prompt and the answer ignored it
    stale      the chunk reached the prompt, and an older superseded chunk outvoted it

The order of those checks is the lesson. Reading the pipeline backwards — "the answer is wrong,
so it is a generation problem" — is what the baseline does, and it scores 14.3%.

Two details make the traces awkward on purpose, because real traces are awkward:

**The answer is usually fluent and uses a real value.** In a retrieval failure the model answers
with a neighbouring chunk's value, which is why the symptom looks like a hallucination. It is not;
the right value never reached the prompt.

**The retrieval score does not tell you where the problem is.** A confident 0.91 on the wrong
chunk is the normal shape of a retrieval failure, not an anomaly.

The corpus is authored from a fact table so that every value is unique and every fault is exact.
`check_labels.py` verifies each injected fault against the trace it claims to produce.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace

STAGES = ("ingestion", "chunking", "query", "retrieval", "packing", "generation", "stale")

FIXES = {
    "ingestion": "reingest",
    "chunking": "rechunk",
    "query": "rewrite",
    "retrieval": "raise_k",  # when the chunk is just below the cut
    "packing": "repack",
    "generation": "ground",
    "stale": "supersede",
}

# Retrieval has two repairs, and which one is right depends on the rank, not on the class.
HYBRID = "hybrid"

N_CASES = 42
K = 5
BUDGET = 400

EXTRA = (
    "The value is reviewed every quarter.",
    "It is measured at the edge, not at the origin.",
    "This applies to production traffic only.",
)

PAIR = {
    "read timeout": "write timeout",
    "write timeout": "read timeout",
    "retry limit": "rate limit",
    "rate limit": "retry limit",
}


@dataclass(frozen=True)
class Doc:
    doc_id: str
    system: str
    values: dict[str, str]


DOCS: tuple[Doc, ...] = (
    Doc(
        "d01",
        "the payments API",
        {
            "read timeout": "30 seconds",
            "write timeout": "60 seconds",
            "retry limit": "5 attempts",
            "rate limit": "600 requests per minute",
            "page threshold": "12 minutes",
            "retention window": "35 days",
        },
    ),
    Doc(
        "d02",
        "the identity service",
        {
            "read timeout": "12 seconds",
            "write timeout": "25 seconds",
            "retry limit": "3 attempts",
            "rate limit": "240 requests per minute",
            "page threshold": "8 minutes",
            "retention window": "90 days",
        },
    ),
    Doc(
        "d03",
        "the search cluster",
        {
            "read timeout": "8 seconds",
            "write timeout": "18 seconds",
            "retry limit": "7 attempts",
            "rate limit": "1200 requests per minute",
            "page threshold": "5 minutes",
            "retention window": "14 days",
        },
    ),
    Doc(
        "d04",
        "the billing worker",
        {
            "read timeout": "20 seconds",
            "write timeout": "40 seconds",
            "retry limit": "4 attempts",
            "rate limit": "300 requests per minute",
            "page threshold": "15 minutes",
            "retention window": "60 days",
        },
    ),
    Doc(
        "d05",
        "the notification relay",
        {
            "read timeout": "45 seconds",
            "write timeout": "90 seconds",
            "retry limit": "6 attempts",
            "rate limit": "900 requests per minute",
            "page threshold": "10 minutes",
            "retention window": "120 days",
        },
    ),
    Doc(
        "d06",
        "the ingest pipeline",
        {
            "read timeout": "15 seconds",
            "write timeout": "35 seconds",
            "retry limit": "9 attempts",
            "rate limit": "450 requests per minute",
            "page threshold": "20 minutes",
            "retention window": "45 days",
        },
    ),
)

PARAMS = tuple(DOCS[0].values)

# Values that appear in no document. Used for answers that invent a number, and for the old
# version of a fact that a leftover chunk still carries.
HALLUCINATED = (
    "42 seconds",
    "6 attempts",
    "750 requests per minute",
    "13 minutes",
    "50 days",
    "9 seconds",
    "2 attempts",
    "480 requests per minute",
    "18 minutes",
    "200 days",
    "75 seconds",
    "11 seconds",
)


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    text: str
    value: str | None = None
    superseded: bool = False


@dataclass(frozen=True)
class Case:
    id: str
    question: str
    rewritten: str
    key_term: str
    gold: str
    stage: str
    fix: str
    ranking: tuple[tuple[str, float], ...]
    prompt_chunks: tuple[str, ...]
    prompt_tokens: int
    budget: int
    packer: str
    answer: str
    index: tuple[Chunk, ...]
    corpus: tuple[Doc, ...]
    raw: str = ""

    @property
    def retrieved(self) -> tuple[str, ...]:
        return tuple(chunk_id for chunk_id, _ in self.ranking[:K])

    @property
    def gold_chunk(self) -> str | None:
        for chunk in self.index:
            if chunk.value == self.gold:
                return chunk.id
        return None

    @property
    def gold_rank(self) -> int | None:
        chunk_id = self.gold_chunk
        if chunk_id is None:
            return None
        for position, (candidate, _) in enumerate(self.ranking, start=1):
            if candidate == chunk_id:
                return position
        return None

    def trace(self) -> str:
        lines = [
            f"question    {self.question}",
            f"rewritten   {self.rewritten}",
            f"ranking     k={K} of {len(self.ranking)} candidates",
        ]
        for position, (chunk_id, score) in enumerate(self.ranking[:8], start=1):
            lines.append(f"  {position:>2}. {chunk_id:<8} {score:.2f}")
        if len(self.ranking) > 8:
            lines.append(f"   .. {len(self.ranking) - 8} more")
        lines.append(
            f"prompt      {len(self.prompt_chunks)} chunks, "
            f"{self.prompt_tokens}/{self.budget} tokens, packer: {self.packer}"
        )
        lines.append(f"answer      {self.answer}")
        return "\n".join(lines)


def contains(haystack: str, needle: str) -> bool:
    """Whole-token containment: `8 seconds` is not inside `18 seconds`."""
    pattern = r"(?<!\w)" + re.escape(needle.casefold()) + r"(?!\w)"
    return re.search(pattern, haystack.casefold()) is not None


def _unit(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:13], 16) / float(16**13)


def _section(doc: Doc, param: str, position: int) -> str:
    return f"The {param} for {doc.system} is {doc.values[param]}. {EXTRA[position % len(EXTRA)]}"


def _full_index() -> list[Chunk]:
    index: list[Chunk] = []
    for doc in DOCS:
        for position, param in enumerate(PARAMS, start=1):
            index.append(
                Chunk(
                    id=f"{doc.doc_id}#{position}",
                    doc_id=doc.doc_id,
                    text=_section(doc, param, position),
                    value=doc.values[param],
                )
            )
    return index


def _split_gold(chunk: Chunk) -> tuple[Chunk, Chunk]:
    """Cut the chunk in the middle of the value, the way a fixed-width chunker does."""
    start = chunk.text.index(chunk.value or "")
    cut = start + max(2, len(chunk.value or "") // 2)
    return (
        Chunk(f"{chunk.id}a", chunk.doc_id, chunk.text[:cut]),
        Chunk(f"{chunk.id}b", chunk.doc_id, chunk.text[cut:]),
    )


def _ranking(index: list[Chunk], gold_id: str | None, top_id: str, gold_rank: int, salt: str):
    """A plausible ranking with the gold moved to the position the fault needs."""
    others = [chunk for chunk in index if chunk.id not in (gold_id, top_id)]
    others.sort(key=lambda chunk: _unit(salt, chunk.id))
    order = [top_id] + [chunk.id for chunk in others]
    if gold_id is not None and gold_rank is not None:
        order.insert(gold_rank - 1, gold_id)
    scored = []
    for position, chunk_id in enumerate(order):
        base = 0.94 - 0.012 * position
        score = round(max(0.11, base - 0.02 * _unit(salt, chunk_id, position)), 3)
        scored.append((chunk_id, score))
    return tuple(scored)


def _make_case(case_id: str, doc: Doc, param: str, stage: str, serial: int) -> Case:
    gold = doc.values[param]
    system = doc.system
    question = f"What is the {param} for {system}?"
    key_term = param.split()[0] if param in PAIR else system.split()[1]

    index = _full_index()
    gold_chunk = next(chunk for chunk in index if chunk.value == gold)

    gold_rank: int | None = 1
    gold_id: str | None = gold_chunk.id
    rewritten = question.lower().rstrip("?")
    packer = "rank order, budget 400"
    history = 150 + int(_unit(case_id, "history") * 90)

    # Apply the fault that changes the index first, then build a ranking over what is left.
    if stage == "ingestion":
        index = [chunk for chunk in index if chunk.doc_id != doc.doc_id]
        gold_id, gold_rank = None, None
    elif stage == "chunking":
        index.remove(gold_chunk)
        first, second = _split_gold(gold_chunk)
        position = next(i for i, chunk in enumerate(index) if chunk.doc_id == doc.doc_id)
        index[position:position] = [first, second]
        gold_id, gold_rank = None, None
    elif stage == "stale":
        old_value = HALLUCINATED[(serial + 6) % len(HALLUCINATED)]
        old_text = f"The {param} for {system} is {old_value}. This page has not been updated."
        index.append(
            Chunk(f"{doc.doc_id}#old", doc.doc_id, old_text, value=old_value, superseded=True)
        )

    # The chunk that ranks first when the question is ambiguous: the confusable sibling if it is
    # still in the index, otherwise the same parameter from the next document.
    if param in PAIR:
        wanted = doc.values[PAIR[param]]
        top_chunk = next((c for c in index if c.doc_id == doc.doc_id and c.value == wanted), None)
    else:
        top_chunk = None
    if top_chunk is None:
        other_doc = DOCS[(DOCS.index(doc) + 1) % len(DOCS)]
        wanted = other_doc.values[param]
        top_chunk = next(c for c in index if c.doc_id == other_doc.doc_id and c.value == wanted)

    if stage == "stale":
        top_chunk = next(chunk for chunk in index if chunk.value == HALLUCINATED[(serial + 6) % len(HALLUCINATED)])
    elif stage == "query":
        rewritten = question.lower().replace(f" {key_term}", "", 1).rstrip("?")
        gold_rank = 6 + serial % 6
    elif stage == "retrieval":
        gold_rank = 6 + serial % 3 if serial % 2 == 0 else 15 + serial % 8
    elif stage == "packing":
        gold_rank = 4
        packer = "dedupe by doc_id, then rank order"
        history = 90 + int(_unit(case_id, "history") * 50)
    elif stage == "generation":
        history = 240 + int(_unit(case_id, "history") * 40)

    ranking = _ranking(index, gold_id, top_chunk.id, gold_rank, case_id)
    retrieved = [chunk_id for chunk_id, _ in ranking[:K]]

    prompt_chunks = tuple(retrieved[:3]) if stage == "packing" else tuple(retrieved[:4])
    chunk_tokens = sum(
        len(next(chunk for chunk in index if chunk.id == chunk_id).text.split())
        for chunk_id in prompt_chunks
    )
    prompt_tokens = 40 + chunk_tokens + history

    if stage == "generation":
        answer = f"The {param} for {system} is {HALLUCINATED[serial % len(HALLUCINATED)]}."
    elif stage == "stale":
        answer = f"The {param} for {system} is {top_chunk.value}."
    elif serial % 2 == 0:
        answer = f"The {param} for {system} is {top_chunk.value}."
    else:
        answer = "I could not find that in the documentation."

    fix = FIXES[stage]
    if stage == "retrieval":
        fix = FIXES["retrieval"] if (gold_rank or 99) <= K + 3 else HYBRID

    case = Case(
        id=case_id,
        question=question,
        rewritten=rewritten,
        key_term=key_term,
        gold=gold,
        stage=stage,
        fix=fix,
        ranking=ranking,
        prompt_chunks=prompt_chunks,
        prompt_tokens=prompt_tokens,
        budget=BUDGET,
        packer=packer,
        answer=answer,
        index=tuple(index),
        corpus=DOCS,
    )
    return replace(case, raw=case.trace())


def build(seed: int = 2027) -> list[Case]:
    pairs = [(doc, param) for doc in DOCS for param in PARAMS]
    cases = []
    for serial in range(N_CASES):
        doc, param = pairs[serial % len(pairs)]
        stage = STAGES[serial % len(STAGES)]
        cases.append(_make_case(f"q{serial + 1:02d}", doc, param, stage, serial))
    return cases


def model():
    """No model is called. The drill is a reading exercise, and the scorecard says so."""

    class NoModel:
        name = "trace-reader"
        cost_usd = 0.0
        latencies: list[float] = []
        n_calls = 0
        calls: list[dict] = []

        def reset(self) -> None:
            self.latencies = []
            self.calls = []

    return NoModel()
