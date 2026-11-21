"""Questions whose evidence lives in specific documents, under a hard budget.

Same forty runbooks as drill 2, different job: not "which document ranks first"
but "which documents fit, and does the evidence survive the cut". A context
window is a budget, and budgets force you to choose.
"""

from __future__ import annotations

from dataclasses import dataclass

from drills.w02_retrieval.data import DOCS, ALIASES, Doc

# Deliberately tight: about three documents fit, and several questions need two.
BUDGET_TOKENS = 120

DOC_INDEX: dict[str, Doc] = {doc.doc_id: doc for doc in DOCS}


@dataclass(frozen=True)
class Question:
    doc_id: str
    text: str
    gold: tuple[str, ...]
    probes: tuple[str, ...]
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.text)


QUESTIONS: tuple[Question, ...] = (
    Question(
        "p01",
        "how do we avoid being throttled, and what should a client do when it happens",
        ("d03", "d04"),
        ("token bucket", "back off"),
    ),
    Question(
        "p02",
        "sign-in is failing and the signing certificate is due for rotation",
        ("d01", "d02"),
        ("assertion consumer", "expire yearly"),
    ),
    Question(
        "p03",
        "we need last night's backup and then a point in time restore",
        ("d05", "d06"),
        ("base backup", "replay WAL"),
    ),
    Question(
        "p04",
        "revert a bad release, then clean up the flags it left behind",
        ("d07", "d08"),
        ("rollback job", "stale flags"),
    ),
    Question(
        "p05",
        "lag is growing and the on-call wants to know when we page",
        ("d11",),
        ("50000 messages",),
    ),
    Question(
        "p06",
        "certificate renewal failing after a nameserver change",
        ("d12", "d13"),
        ("internal CA", "300 second TTL"),
    ),
    Question(
        "p07",
        "purging the CDN quickly without waiting for every edge",
        ("d14",),
        ("purge by tag",),
    ),
    Question(
        "p08",
        "audit records and how long we are allowed to keep them",
        ("d15",),
        ("400 days",),
    ),
    Question(
        "p09",
        "rotating a service credential without taking the service down",
        ("d16",),
        ("rotate every 90 days",),
    ),
    Question(
        "p10",
        "the build got slow right after someone bumped a dependency",
        ("d17",),
        ("lockfile hash",),
    ),
    Question(
        "p11",
        "a test fails occasionally; should we just retry it",
        ("d18",),
        ("quarantined",),
    ),
    Question(
        "p12",
        "duplicate payment webhooks and a client retrying the same charge",
        ("d19", "d29"),
        ("idempotent", "Idempotency-Key"),
    ),
    Question(
        "p13",
        "rounding on invoice totals and recovering customers whose cards fail",
        ("d20", "d21"),
        ("minor units", "dunning sequence"),
    ),
    Question(
        "p14",
        "a customer asks us to delete everything, including the backups",
        ("d23", "d24"),
        ("search index", "newline-delimited"),
    ),
    Question(
        "p15",
        "keeping personal data out of the log pipeline",
        ("d25",),
        ("redacts email",),
    ),
    Question(
        "p16",
        "push tokens going stale and when we are allowed to send an SMS",
        ("d32", "d34"),
        ("unregistered", "transactional alerts"),
    ),
    Question(
        "p17",
        "chunk sizes for the vector index and how much memory that needs",
        ("d37", "d38"),
        ("1536 dimensions", "15 percent overlap"),
    ),
    Question(
        "p18",
        "prompt caching keeps missing and the primary model keeps erroring",
        ("d39", "d40"),
        ("five minutes", "falls back"),
    ),
)


def corpus() -> list[Question]:
    return list(QUESTIONS)


def count_tokens(text: str) -> int:
    return len(text.split())


def aliases() -> dict[str, tuple[str, ...]]:
    return ALIASES
