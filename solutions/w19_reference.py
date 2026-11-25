"""Reference solution for the memory drill: a fact ledger plus the last six turns.

Twelve facts, one line each, about forty-five tokens of memory. The conversation is six hundred
and fifty tokens, so the ledger compresses it roughly fourteen to one and loses none of the
facts. Adding the last six turns takes the memory to about ninety tokens, still barely half the
budget, and that window is not there for the facts: it is there for the detail nobody thought to
put in the schema. `sweep.py` measures the difference — the ledger alone drops the one probe that
is not a fact, and the window brings it back.

Two decisions carry the score.

**Latest wins, but a negated mention is not a mention.** The postcode is stated at turn twelve,
then corrected at turn twenty-eight with the old value repeated inside the correction: "the
postcode is SW1A 2AA, not SW1A 1AA". Taking the first match keeps the old one; taking the last
match *also* keeps the old one, because the old value is the last string in the sentence. The
rule that works is "the last mention that is not preceded by `not`" — which is what a person
does when they read the sentence, and what a naive extractor does not.

**Extraction beats summarisation here.** A rolling summary has to spend its budget on prose and
corrupts numbers under pressure; a ledger spends 45 tokens on the twelve things that will be
asked about. `sweep.py` measures both. If the probes asked about tone or an unresolved worry,
the ranking would change — see the last section of `spec.md`.
"""

from __future__ import annotations

import re

from drills.w19_memory.data import RECENT_TURNS

MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
)

# slot -> (label, pattern). Every pattern captures exactly the value.
PATTERNS: tuple[tuple[str, str, str], ...] = (
    # Three openings in the corpus: "I'm Dana Okafor", "this is Marcus Bell", "I'm Priya Raman".
    ("name", "name", r"\b(?:I'm|this is) ([A-Z][\w'-]+ [A-Z][\w'-]+)"),
    ("email", "email", r"\b([\w.+-]+@[\w.-]+\.\w+)"),
    ("order", "order", r"\b([A-F]-\d{4})\b"),
    ("plan", "plan", r"\bon the (Standard|Plus|Business) plan\b"),
    ("allergy", "allergy", r"\ballergic to ([a-z]+)\b"),
    ("budget", "budget", r"£([\d,]+)"),
    ("postcode", "postcode", r"\b([A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2})\b"),
    ("date", "date", rf"\b(\d{{1,2}} {MONTH})\b"),
    ("window", "window", r"\bbetween (\d{1,2} and \d{1,2})\b"),
    ("reference", "reference", r"\b(REF-\d+)\b"),
    ("recipient", "recipient", r"\bleave it with ([^.]+?) and the gate code\b"),
    ("gate", "gate", r"\bgate code is (\d+)\b"),
)

NEGATION = re.compile(r"(?:\bnot|\binstead of)\s+$", re.IGNORECASE)


def _negated(text: str, start: int) -> bool:
    return NEGATION.search(text[max(0, start - 14) : start]) is not None


def _latest(text: str, pattern: str) -> str | None:
    matches = list(re.finditer(pattern, text))
    if not matches:
        return None
    kept = [match for match in matches if not _negated(text, match.start())]
    return (kept or matches)[-1].group(1).strip()


def ledger(transcript: str) -> str:
    lines = []
    for _, label, pattern in PATTERNS:
        value = _latest(transcript, pattern)
        if value is not None:
            lines.append(f"{label}: {value}")
    return "\n".join(lines)


def remember(conversation, model) -> list[str]:
    recent = "\n".join(conversation.turns[-RECENT_TURNS:])
    memory = ledger(conversation.transcript) + "\n" + recent
    return [model.answer(probe, memory) for probe in conversation.probes]
