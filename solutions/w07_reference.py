"""Reference solution for drill 7 — read this after trying your own.

Two defects, two different fixes:

  - **Position bias** is a *systematic* error. Ask the same question twice with
    the responses swapped. If the judge says "A" both times, it is agreeing with
    itself across both positions, which is real evidence. If it says "A" then
    "B", it was reading the position, not the content — and you should not trust
    either verdict.

  - **Noise** is random. You cannot swap it away; you can only outvote it. With
    two samples you have a tie; with three you have a majority.

The budget is what makes this interesting. Two calls per pair is $0.0144, right
under the cap. Three is $0.0216 and fails. So the design constraint is: spend the
second sample on the pairs where it can still change the answer.
"""

from __future__ import annotations

PROMPT = """Which response is better for the question? Answer with one line:
Winner: A, Winner: B, or Winner: tie.

Question: {question}

RESPONSE A:
{a}

RESPONSE B:
{b}
"""


def _parse(text: str) -> str:
    lowered = text.casefold()
    if "tie" in lowered:
        return "tie"
    if "winner: a" in lowered:
        return "A"
    if "winner: b" in lowered:
        return "B"
    return "tie"


def _ask(model, pair, swap: bool, salt: int) -> str:
    """One judgement. `salt` varies the prompt, which is what makes a repeat a
    genuinely new sample: a deterministic system given identical input returns an
    identical answer, so re-asking the same question is not sampling."""
    first, second = (pair.b, pair.a) if swap else (pair.a, pair.b)
    prompt = f"(sample {salt})\n" + PROMPT.format(
        question=pair.question, a=first, b=second
    )
    raw = model.complete(prompt).text
    verdict = _parse(raw)

    if not swap:
        return verdict
    # Undo the swap so both calls speak the same coordinate system.
    return {"A": "B", "B": "A", "tie": "tie"}[verdict]


def judge(pair, model) -> str:
    # Position bias always favours whichever response is printed first. So the
    # samples must *balance* the order: two forward, two swapped. An odd number
    # of samples silently re-introduces the bias, because the extra sample is
    # always in one order.
    samples = [
        _ask(model, pair, swap=False, salt=0),
        _ask(model, pair, swap=True, salt=1),
        _ask(model, pair, swap=False, salt=2),
        _ask(model, pair, swap=True, salt=3),
    ]

    # Plurality over all three outcomes. Dropping abstentions biases the result
    # toward whichever answer survived, which is how a tie turns into a confident
    # "A" that nobody voted for.
    tally = {"A": samples.count("A"), "B": samples.count("B"), "tie": samples.count("tie")}
    best = max(tally.values())
    winners = [label for label, count in tally.items() if count == best]
    return winners[0] if len(winners) == 1 else "tie"
