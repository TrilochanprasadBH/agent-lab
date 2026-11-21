"""Reference solution for drill 6 — read this after trying your own.

A grader that generalises encodes the *reason* a reply is good. Four checks, and
not one of them is a surface statistic:

  1. **No placeholders.** `[NAME]`, `TODO`, `{{...}}` mean nobody finished the
     reply. This is a fact about the artifact, not about the split.
  2. **No policy violations.** Refunds are 30 days. A reply promising 90 days is
     wrong no matter how politely it is written.
  3. **No empty commitment.** "I'll look into it", "get back to you", "as soon as
     possible" and "guaranteed" are all ways of saying nothing, or of promising
     more than anyone can deliver.
  4. **Concrete and on topic.** There must be a number (a reference, a timeframe)
     *and* the reply must actually address the customer's subject.

The two things this deliberately does *not* use — length, and the word "Thanks" —
are exactly the two things that separate train from test. That is the whole
lesson: an eval is a model of quality, and a model fitted to one sample of writers
is not a model of quality.
"""

from __future__ import annotations

import re

STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "was", "are", "be", "my", "our", "we", "you", "your", "i", "it", "this",
    "that", "can", "get", "has", "have", "was", "supposed", "never",
}

PLACEHOLDERS = ("[name]", "[customer]", "{{", "}}", "todo", "xxxx", "<insert")
VAGUE = (
    "look into it",
    "get back to you",
    "as soon as possible",
    "at your earliest",
    "speak to the right team",
)
OVERCLAIM = ("guaranteed", "definitely", "for sure", "100%")
RUDE = ("not our problem", "should have known", "nothing we can do")
WRONG_POLICY = ("90 days", "lifetime", "no questions asked")


def _stem(word: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            word = word[: -len(suffix)]
            break
    if len(word) > 4 and word.endswith("e"):
        word = word[:-1]
    return word


def _salient(text: str) -> set[str]:
    return {
        _stem(word)
        for word in re.findall(r"[a-z]+", text.casefold())
        if len(word) > 4 and word not in STOPWORDS
    }


def grade(reply, model) -> bool:
    text = reply.text.casefold()

    if any(marker in text for marker in PLACEHOLDERS):
        return False
    if any(marker in text for marker in WRONG_POLICY):
        return False
    if any(marker in text for marker in OVERCLAIM):
        return False
    if any(marker in text for marker in VAGUE):
        return False
    if any(marker in text for marker in RUDE):
        return False

    # A reply with no number commits to nothing specific.
    if not re.search(r"\d", text):
        return False

    # An apology is not an action. Something has to be promised, or undone.
    commitments = (
        "within", "business day", "minute", "reversed", "reissued",
        "raised", "re-sent", "out for delivery", "is sorted",
    )
    if not any(marker in text for marker in commitments):
        return False

    # It has to answer the question that was asked.
    shared = _salient(reply.question) & _salient(reply.text)
    return len(shared) >= 1
