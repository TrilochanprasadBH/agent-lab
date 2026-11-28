"""Reference solution: filter by what is possible, filter by what is good enough, take the cheapest.

Three passes over three options. The order is the whole solution.

**Possible first.** A fine-tune needs examples, a stopped world and no citation requirement. Facts
that change weekly are not a training problem, they are a rebuild loop that never converges. A
retrieval system needs a corpus. Sending a request to an option that cannot work is not an
optimisation, it is a bug, and the sweep shows what it costs to skip this pass.

**Good enough second.** Measured quality, per scenario, against the bar. The cheapest option in
the table is regularly below the bar — the small model on medical coding, the prompt-only
assistant on anything that needs a source. Optimising the third decimal of cost for an answer
that fails the eval is the most common version of this mistake.

**Cheapest last.** Per day, not per request, because a fine-tune pays for training once and the
whole argument is that the fixed cost amortises. Per *day* is the unit that makes the crossover
visible: at twenty requests a day the training is the bill; at twenty thousand it is a rounding
error.

If nothing survives the first two passes the answer is `none`. That is a real outcome and the
correct one: the requirement is not achievable with the options on the table, and shipping the
least bad option is how teams end up defending a system they know is under the bar.
"""

from __future__ import annotations

from drills.w23_finetune.data import (
    APPROACHES,
    EPOCHS,
    LARGE_IN,
    LARGE_OUT,
    RETRIEVAL_FEE,
    SMALL_IN,
    SMALL_OUT,
    TRAIN_PER_MTOKEN,
    WINDOW_DAYS,
)


def daily_cost(scenario, approach: str) -> float:
    requests = scenario.requests
    if approach == "prompting":
        return requests * (
            scenario.prompt_tokens * LARGE_IN + scenario.output_tokens * LARGE_OUT
        ) / 1e6
    if approach == "rag":
        return (
            requests
            * (
                (scenario.prompt_tokens + scenario.retrieved_tokens) * LARGE_IN
                + scenario.output_tokens * LARGE_OUT
            )
            / 1e6
            + requests * RETRIEVAL_FEE
        )
    training = (
        scenario.examples * EPOCHS * scenario.example_tokens * TRAIN_PER_MTOKEN / 1e6
    )
    return (
        requests * (scenario.prompt_tokens * SMALL_IN + scenario.output_tokens * SMALL_OUT) / 1e6
        + training / WINDOW_DAYS[scenario.facts]
    )


def possible(scenario, approach: str) -> bool:
    if approach == "prompting":
        return True
    if approach == "rag":
        return scenario.corpus
    return (
        scenario.examples > 0
        and scenario.facts != "weekly"
        and not scenario.citations
    )


def quality(scenario, approach: str) -> float:
    return scenario.quality[APPROACHES.index(approach)]


def choose(scenario, model) -> str:
    options = [
        approach
        for approach in APPROACHES
        if possible(scenario, approach) and quality(scenario, approach) >= scenario.bar
    ]
    if not options:
        return "none"
    return min(options, key=lambda approach: (daily_cost(scenario, approach), APPROACHES.index(approach)))
