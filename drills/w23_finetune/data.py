"""Twenty-four architecture decisions, and the arithmetic that makes each one.

The question "should we prompt, retrieve, or fine-tune" is usually answered with a preference. It
is a decision with a computable answer, and the computation is short:

    filter the options by what is possible
    filter again by what meets the quality bar
    among the survivors, take the cheapest per day

Each scenario is a product with a volume, a prompt and output size, a retrieval corpus, a set of
labelled examples, how often the facts change, and three quality numbers measured on that
product's eval set. None of the quality numbers is assumed; they are inputs, because the entire
point is that you measure them for *your* task rather than believing a blog post.

The costs:

    prompting    a large model, $3.00 per million input tokens and $15.00 per million output
    rag          the same model, plus the retrieved tokens on every call, plus a retrieval fee
    fine-tune    a small model at a tenth of the price, plus training, amortised over the window
                 in which the facts stay still

Two things follow from that, and they are the two things people get wrong.

**Fine-tuning is a volume business.** Training is a fixed cost; the saving per request is small.
At twenty requests a day the training dominates and prompting wins. At twenty thousand a day the
small model is fifteen times cheaper and the training is noise. The crossover is arithmetic, not
taste.

**A constraint can beat the spreadsheet.** Facts that change weekly rule out fine-tuning however
cheap it is, a requirement to cite sources rules it out however accurate it is, and no examples
rule it out however much budget you have. The cheapest option in the table is regularly a
non-option, which is why the sweep includes a strategy that ignores the constraints and a
strategy that ignores the quality bar.

And sometimes the honest answer is `none`: every option you have is below the bar, and the right
move is to say so rather than ship the least bad one.

The scenarios are authored, because the decision depends on exact numbers and a known constraint
set. `check_labels.py` recomputes every cost with a second implementation and asserts that each
stored answer is the unique cheapest option that clears the bar.
"""

from __future__ import annotations

from dataclasses import dataclass

APPROACHES = ("prompting", "rag", "finetune")
ANSWERS = APPROACHES + ("none",)

# Dollars per million tokens.
LARGE_IN = 3.0
LARGE_OUT = 15.0
SMALL_IN = 0.3
SMALL_OUT = 1.2
TRAIN_PER_MTOKEN = 8.0
EPOCHS = 3

# Dollars per request, for embedding the query and searching the index.
RETRIEVAL_FEE = 0.0004

# How long the fine-tune stays valid, in days. "weekly" is not a window, it is a rebuild loop.
WINDOW_DAYS = {"never": 365, "monthly": 30, "weekly": 7}


@dataclass(frozen=True)
class Scenario:
    id: str
    summary: str
    kind: str  # cost, constraint, none
    requests: int  # per day
    prompt_tokens: int
    output_tokens: int
    retrieved_tokens: int
    examples: int
    example_tokens: int
    facts: str  # never, monthly, weekly
    citations: bool
    corpus: bool
    quality: tuple[float, float, float]  # prompting, rag, finetune
    bar: float


def S(*args, **kwargs) -> Scenario:
    return Scenario(*args, **kwargs)


SCENARIOS: tuple[Scenario, ...] = (
    # -- cost decides: every option is possible, at least two clear the bar ----------------
    S("t01", "Refund decisions on a 40k-ticket archive, 20k a day, facts never change",
      "cost", 20000, 900, 250, 700, 5000, 600, "never", False, True,
      (0.86, 0.94, 0.93), 0.90),
    S("t02", "The same refund assistant, but twenty requests a day and a looser bar",
      "cost", 20, 900, 250, 700, 5000, 600, "never", False, True,
      (0.86, 0.94, 0.93), 0.85),
    S("t03", "Policy answers with a long retrieved context, 5k a day, retrained monthly",
      "cost", 5000, 400, 150, 1200, 2000, 400, "monthly", False, True,
      (0.81, 0.93, 0.91), 0.90),
    S("t04", "A frozen 2019 manual, 50k a day, 15k examples",
      "cost", 50000, 700, 250, 900, 15000, 650, "never", False, True,
      (0.79, 0.92, 0.90), 0.89),
    S("t05", "Long contract questions, 100 a day, 30k labelled answers",
      "cost", 100, 2000, 600, 800, 30000, 1200, "never", False, True,
      (0.88, 0.92, 0.93), 0.87),
    S("t06", "Support drafting over a monthly policy update, 8k a day",
      "cost", 8000, 1000, 350, 600, 4000, 500, "monthly", False, True,
      (0.80, 0.95, 0.92), 0.90),
    S("t07", "Answers about a product catalogue, 2k a day", 
      "cost", 2000, 600, 200, 500, 3000, 400, "monthly", False, True,
      (0.84, 0.91, 0.93), 0.90),
    S("t08", "Product copy in a house style, 40k a day, 8k examples",
      "cost", 40000, 250, 500, 300, 8000, 700, "never", False, True,
      (0.88, 0.93, 0.96), 0.92),
    S("t09", "A 400-category classifier, 60k a day, 30k examples",
      "cost", 60000, 400, 40, 200, 30000, 300, "never", False, True,
      (0.83, 0.90, 0.97), 0.90),
    S("t10", "Short internal lookups, 300 a day, 8k examples",
      "cost", 300, 1200, 300, 700, 8000, 600, "never", False, True,
      (0.86, 0.93, 0.92), 0.90),

    # -- a constraint removes the cheapest option ------------------------------------------
    S("t11", "Ticket triage over a taxonomy, 25k a day, facts change weekly",
      "constraint", 25000, 500, 80, 400, 7000, 400, "weekly", False, True,
      (0.87, 0.91, 0.94), 0.90),
    S("t12", "Support replies with mandatory source links, 12k a day, 20k examples",
      "constraint", 12000, 800, 300, 900, 20000, 600, "never", True, True,
      (0.83, 0.95, 0.94), 0.92),
    S("t13", "A 12-class routing taxonomy, 15k a day, no labelled examples yet",
      "constraint", 15000, 600, 120, 500, 0, 0, "monthly", False, True,
      (0.84, 0.92, 0.92), 0.90),
    S("t14", "Meeting notes in a fixed format, 5k a day, no corpus, 4k examples",
      "constraint", 5000, 300, 180, 0, 4000, 500, "monthly", False, False,
      (0.85, 0.0, 0.94), 0.90),
    S("t15", "Tone rewriting, 150 a day, no corpus, 2k examples",
      "constraint", 150, 400, 150, 0, 2000, 400, "monthly", False, False,
      (0.86, 0.0, 0.93), 0.85),
    S("t16", "Answers about yesterday's outages, 3k a day, no corpus, 5k examples",
      "constraint", 3000, 700, 200, 0, 5000, 600, "weekly", False, False,
      (0.82, 0.0, 0.90), 0.80),
    S("t17", "FAQ drafting, 4k a day, no examples, a corpus that is good enough",
      "constraint", 4000, 300, 100, 400, 0, 0, "monthly", False, True,
      (0.84, 0.90, 0.88), 0.80),
    S("t18", "Field extraction from a fixed invoice layout, 9k a day, no corpus",
      "constraint", 9000, 500, 120, 0, 6000, 800, "monthly", False, False,
      (0.86, 0.0, 0.95), 0.93),

    # -- nothing clears the bar ------------------------------------------------------------
    S("t19", "Medical coding from clinical notes, 10k a day, 50k examples",
      "none", 10000, 1600, 150, 500, 50000, 1000, "monthly", False, True,
      (0.71, 0.82, 0.88), 0.95),
    S("t20", "Multi-hop questions over nine disconnected systems, 1200 a day",
      "none", 1200, 1100, 400, 900, 4000, 700, "weekly", False, True,
      (0.62, 0.79, 0.75), 0.90),
    S("t21", "Contract drafting in a jurisdictional style, 80 a day, no examples",
      "none", 80, 3000, 900, 1500, 0, 0, "monthly", True, True,
      (0.68, 0.81, 0.0), 0.92),
    S("t22", "Real-time translation of support chat, 20k a day, no corpus",
      "none", 20000, 400, 300, 0, 2000, 500, "never", False, False,
      (0.74, 0.0, 0.85), 0.93),
    S("t23", "Summarising legal filings at partner quality, 500 a day",
      "none", 500, 4000, 800, 1000, 8000, 1200, "monthly", False, True,
      (0.66, 0.78, 0.80), 0.90),
    S("t24", "Answers about a weekly-changing wiki, 3k a day, no examples",
      "none", 3000, 900, 200, 600, 0, 0, "weekly", False, True,
      (0.80, 0.88, 0.0), 0.90),
)

# Filled in below by `check_labels`' twin implementation, one entry per scenario id.
TRUTH: dict[str, str] = {
    "t01": "finetune",
    "t02": "prompting",
    "t03": "finetune",
    "t04": "finetune",
    "t05": "prompting",
    "t06": "finetune",
    "t07": "finetune",
    "t08": "finetune",
    "t09": "finetune",
    "t10": "finetune",
    "t11": "rag",
    "t12": "rag",
    "t13": "rag",
    "t14": "finetune",
    "t15": "prompting",
    "t16": "prompting",
    "t17": "prompting",
    "t18": "finetune",
    "t19": "none",
    "t20": "none",
    "t21": "none",
    "t22": "none",
    "t23": "none",
    "t24": "none",
}


def build(seed: int = 2027) -> list[Scenario]:
    return list(SCENARIOS)


def model():
    """No model is called: the decision is arithmetic over the scenario."""

    class NoModel:
        name = "cost-model"
        cost_usd = 0.0
        latencies: list[float] = []
        n_calls = 0
        calls: list[dict] = []

        def reset(self) -> None:
            self.latencies = []
            self.calls = []

    return NoModel()
