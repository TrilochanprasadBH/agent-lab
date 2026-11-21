"""Support replies, human-labelled, split into a visible train set and a hidden
test set.

The trap is deliberate and it is the most useful thing in this drill.

In the train set, every good reply happens to open with "Thanks for…" and happen
to be long. Both of those correlate with quality *in that split only*, because
one writing team produced all of it. In the test set, good replies are short and
open differently.

A grader built on length or on the word "Thanks" will look excellent on train and
land near a coin flip on anything new. That is what overfitting an eval looks
like, and it is indistinguishable from success until you measure on data you did
not look at.

Please do not import `hidden_labels` to cheat. The drill is the discipline, not
the number.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

ISSUES = [
    (
        "refund",
        "I was charged twice for order {ref}, can I get a refund?",
        "the duplicate charge is being reversed",
        "The duplicate charge on {ref} is reversed",
        ("duplicate", "charge", "refund"),
    ),
    (
        "password",
        "The password reset email never arrives for {ref}.",
        "I have re-sent the reset link to {ref}",
        "Reset link re-sent to {ref}, valid for 30 minutes",
        ("password", "reset", "email"),
    ),
    (
        "billing",
        "My invoice {ref} shows the wrong amount.",
        "the corrected invoice has been reissued",
        "Corrected invoice reissued, so {ref} now shows the right amount",
        ("invoice", "amount", "charged"),
    ),
    (
        "ratelimit",
        "Our integration keeps hitting rate limits at peak hours.",
        "your limit is raised to 1200 requests per minute",
        "Rate limit raised to 1200 requests per minute",
        ("rate", "limit", "integration"),
    ),
    (
        "shipping",
        "Order {ref} was supposed to arrive last week.",
        "the parcel is out for delivery",
        "Order {ref} is out for delivery",
        ("order", "arrive", "parcel"),
    ),
]

REF_POOL = ["8712", "8713", "9000", "4410", "2277", "6601"]
EMAIL_POOL = ["ops@aster.example", "hi@bell.example", "it@corvid.example"]

# Train-set goods: long, and they all open the same way.
GOOD_TRAIN = [
    "Thanks for getting in touch about this. I've pulled up {ref} and can confirm "
    "that {fix}. It should be fully resolved within {days} business days; if it "
    "is not, reply here with the reference and I will take it further myself.",
    "Thanks for flagging this, and sorry for the trouble on {ref}. I have checked "
    "the account and {fix}. Expect that to settle within {days} business days, and "
    "if anything still looks wrong after that, reply on this thread and I will "
    "reopen it for you directly.",
]

# Test-set goods: short, different openers, no "Thanks", and they name the issue.
GOOD_TEST = [
    "{fix_cap}. It should settle within {days} business days; reply here if it does not.",
    "{fix_cap} — {days} business days is the usual window.",
]

BAD = [
    "Thanks for your message about {ref}. [NAME], I have asked the team to look at "
    "the duplicate charge and they will reply shortly with an update for you.",
    "Thanks for reaching out. Our refunds are available within 90 days of purchase, "
    "so you are covered for the duplicate charge on {ref}.",
    "I will look into the duplicate charge on {ref} and get back to you as soon as "
    "possible once I have spoken to the right team about it.",
    "This is a known issue with duplicate charges.",
    "I have guaranteed that the refund will land today, for sure, on {ref}.",
    "Your parcel is out for delivery and should reach you this afternoon; tracking "
    "updates for {ref} are enabled again.",
    "Duplicate charges happen sometimes and honestly that is not our problem.",
    "We are sorry for the inconvenience caused by the duplicate charge on {ref}.",
    "Thanks for the note. TODO: confirm with finance before replying about {ref}.",
]


@dataclass(frozen=True)
class Reply:
    doc_id: str
    question: str
    text: str
    split: str
    raw: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw", self.text)


def _fixture(rng: random.Random) -> dict[str, str]:
    ref = rng.choice(REF_POOL)
    email = rng.choice(EMAIL_POOL)
    return {"ref": ref, "email": email, "days": rng.choice(["2", "3", "5", "7"])}


def build() -> tuple[list[Reply], dict[str, int]]:
    rng = random.Random(2027)
    replies: list[Reply] = []
    labels: dict[str, int] = {}
    counter = 0

    # -- train: 70 good (long, "Thanks…"), 70 bad (varied) -----------------
    for index in range(140):
        issue, question, fix, fix_cap, _words = ISSUES[index % len(ISSUES)]
        fixture = _fixture(rng)
        good = index % 2 == 0
        if good:
            template = rng.choice(GOOD_TRAIN)
            text = template.format(fix=fix, ref=fixture["ref"], days=fixture["days"])
        else:
            template = BAD[(index // 2) % len(BAD)]
            text = template.format(ref=fixture["ref"])
        counter += 1
        doc_id = f"train-{counter:03d}"
        replies.append(
            Reply(
                doc_id=doc_id,
                question=question.format(ref=fixture["ref"], email=fixture["email"]),
                text=text,
                split="train",
            )
        )
        labels[doc_id] = 1 if good else 0

    # -- test: 35 good (short, varied), 35 bad -----------------------------
    for index in range(70):
        issue, question, fix, fix_cap, _words = ISSUES[index % len(ISSUES)]
        fixture = _fixture(rng)
        good = index % 2 == 0
        if good:
            template = rng.choice(GOOD_TEST)
            text = template.format(
                fix=fix,
                fix_cap=fix_cap.format(ref=fixture["ref"], email=fixture["email"]),
                ref=fixture["ref"],
                email=fixture["email"],
                days=fixture["days"],
            )
        else:
            template = BAD[(index // 2) % len(BAD)]
            text = template.format(ref=fixture["ref"])
        counter += 1
        doc_id = f"test-{counter:03d}"
        replies.append(
            Reply(
                doc_id=doc_id,
                question=question.format(ref=fixture["ref"], email=fixture["email"]),
                text=text,
                split="test",
            )
        )
        labels[doc_id] = 1 if good else 0

    return replies, labels


_ALL, LABELS = build()


def corpus() -> list[Reply]:
    return [reply for reply in _ALL if reply.split == "test"]


def train_examples() -> list[tuple[Reply, int]]:
    return [(reply, LABELS[reply.doc_id]) for reply in _ALL if reply.split == "train"]


def hidden_labels() -> dict[str, int]:
    return dict(LABELS)
