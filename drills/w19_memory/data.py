"""Six support conversations, a fixed memory budget, and a model that answers from what it is given.

The shape of the problem is the one every long-running assistant hits. A conversation is longer
than the context the next call can afford, so something has to be dropped. Which something is
the whole design question, and the conversation is built so that the answer is not "keep the
most recent":

- some facts are stated early and never repeated (name, email, order, plan)
- three are constraints stated in the middle that the assistant must honour (allergy, budget,
  time window)
- two are **corrected** later: the postcode and the delivery date. The old value appears first
  and the correction names it again ("... SW1A 2AA, not SW1A 1AA"), so "take the last match"
  and "take the first match" both get the wrong answer
- three arrive at the very end (complaints reference, who to leave the parcel with, gate code)
- one detail is not a fact at all: the customer mentions, in the last six turns, that they tried
  the chat first. No fact schema anticipates it, and both the truncation window and the summary
  keep it for free. That is the probe that shows what a ledger costs you.

A policy that keeps the last N turns therefore gets the last three and the unstructured detail
for free, loses everything else, and never sees a correction. A policy that summarises keeps more
but corrupts numbers. A policy that extracts facts into a ledger keeps all twelve in about thirty
tokens and drops the detail nobody schematised.

The model here is a reader, not a reasoner: `answer` looks for the value in the memory it was
handed, falls back to the stale value if that is what the memory contains, and otherwise
confabulates from another conversation's value or says it does not know. That is deliberately
simple — the drill measures what you chose to keep, not how well a model paraphrases.

    budget          160 whitespace tokens of memory per answer call
    conversation    60 turns, 648 to 654 tokens
    probes          13 per conversation, 78 in total

Supersession matters more than people expect. In this corpus the postcode's old value appears
twice — once when the customer states the address, once inside the correction that rejects it —
so a memory that keeps every mention is not just wasteful, it is wrong.

"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# Whitespace tokens, same convention as w03: crude, but identical for every policy.
BUDGET_TOKENS = 160

# The reference keeps this many turns verbatim for continuity and puts the facts in a ledger.
RECENT_TURNS = 6

# A missing fact does not produce silence. This is the share of the time the model invents a
# plausible value from another conversation instead of admitting it does not know.
CONFABULATE = 0.40

MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def count_tokens(text: str) -> int:
    return len(text.split())


@dataclass(frozen=True)
class Facts:
    name: str
    email: str
    order: str
    plan: str
    allergy: str
    budget: str
    postcode_old: str
    postcode_new: str
    date_old: str
    date_new: str
    window: str
    reference: str
    recipient: str
    gate: str
    tried: str

    @property
    def first(self) -> str:
        return self.name.split()[0]

    @property
    def old_day(self) -> str:
        """`12 March` -> `12th`, so the correction does not repeat the old date in full."""
        return _ordinal(self.date_old.split()[0])

    @property
    def values(self) -> dict[str, str]:
        return {
            "name": self.name,
            "email": self.email,
            "order": self.order,
            "plan": self.plan,
            "allergy": self.allergy,
            "budget": self.budget,
            "postcode": self.postcode_new,
            "date": self.date_new,
            "window": self.window,
            "reference": self.reference,
            "recipient": self.recipient,
            "gate": self.gate,
            "tried": self.tried,
        }


def _ordinal(day: str) -> str:
    n = int(day)
    if 11 <= n % 100 <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


FACTS: tuple[Facts, ...] = (
    Facts(
        name="Dana Okafor",
        email="dana.okafor@example.com",
        order="A-4471",
        plan="Plus",
        allergy="shellfish",
        budget="1,200",
        postcode_old="SW1A 1AA",
        postcode_new="SW1A 2AA",
        date_old="12 March",
        date_new="14 March",
        window="9 and 11",
        reference="REF-88213",
        recipient="the neighbour at 14B",
        gate="3311",
        tried="the chat",
    ),
    Facts(
        name="Marcus Bell",
        email="marcus.bell@example.net",
        order="B-2098",
        plan="Standard",
        allergy="peanuts",
        budget="800",
        postcode_old="M1 4BT",
        postcode_new="M1 5QA",
        date_old="3 April",
        date_new="5 April",
        window="10 and 12",
        reference="REF-31077",
        recipient="the front desk",
        gate="2044",
        tried="the phone line",
    ),
    Facts(
        name="Priya Raman",
        email="priya.raman@example.org",
        order="C-7730",
        plan="Business",
        allergy="sesame",
        budget="2,400",
        postcode_old="EH1 2NG",
        postcode_new="EH2 4LH",
        date_old="22 May",
        date_new="24 May",
        window="8 and 10",
        reference="REF-55409",
        recipient="the concierge",
        gate="1180",
        tried="the FAQ page",
    ),
    Facts(
        name="Tomas Novak",
        email="tomas.novak@example.com",
        order="D-1166",
        plan="Plus",
        allergy="shellfish",
        budget="1,500",
        postcode_old="CF10 3AT",
        postcode_new="CF11 9HB",
        date_old="9 June",
        date_new="11 June",
        window="13 and 15",
        reference="REF-77124",
        recipient="the neighbour at 6A",
        gate="7302",
        tried="the callback request",
    ),
    Facts(
        name="Aisha Khan",
        email="aisha.khan@example.net",
        order="E-6420",
        plan="Standard",
        allergy="nuts",
        budget="950",
        postcode_old="G1 1XW",
        postcode_new="G2 6QQ",
        date_old="18 July",
        date_new="20 July",
        window="11 and 13",
        reference="REF-20988",
        recipient="the front desk",
        gate="5567",
        tried="the chatbot",
    ),
    Facts(
        name="Leo Andersen",
        email="leo.andersen@example.org",
        order="F-9033",
        plan="Business",
        allergy="dairy",
        budget="1,800",
        postcode_old="BS1 5TR",
        postcode_new="BS8 2PN",
        date_old="2 August",
        date_new="4 August",
        window="14 and 16",
        reference="REF-66031",
        recipient="the neighbour at 22C",
        gate="9048",
        tried="the web form",
    ),
)

OPENINGS = (
    "Hi, I'm {name} — I think my account is in a mess.",
    "Hello, this is {name}. Something has gone wrong with my order.",
    "Morning — I'm {name}, and I need help with a delivery.",
)
GREETINGS = (
    "Happy to help, {first}. What's happening?",
    "Of course, {first}. Tell me what you're seeing.",
    "Hello {first}. Let's sort it out — what's the problem?",
)
PROBLEMS = (
    "I placed an order last week and it hasn't moved since Tuesday.",
    "The tracking has said label created for four days now.",
    "My order was meant to arrive on Tuesday and nothing has happened.",
)
FILLERS = (
    (
        "That's what I thought. The app is not much help either.",
        "The app is being rewritten, which does not help you today.",
    ),
    (
        "I did try the help pages first, but they went in circles.",
        "I'm sorry about that. You have a real person now.",
    ),
    (
        "Fine. Is there anything I need to do before then?",
        "Just make sure someone is in for the whole window.",
    ),
    (
        "I'll be working from home, so that is fine.",
        "Then you are set.",
    ),
    (
        "Thanks. The old one still shows in the app sometimes.",
        "The app caches it. It will refresh within the hour.",
    ),
    (
        "Oh — thank you. I expected to pay it.",
        "It's the least we can do after the courier issue.",
    ),
    (
        "Perfect. That takes a weight off.",
        "Glad to hear it.",
    ),
    (
        "One more thing — will the courier call before arriving?",
        "They usually do, but the app is the reliable place to look.",
    ),
    (
        "The app still shows the old address, which is why I ask.",
        "It will catch up once the change propagates tonight.",
    ),
    (
        "And the tracking page has not refreshed since this morning.",
        "The courier only scans at the depot, so that is normal.",
    ),
    (
        "Understood. I will keep an eye on it.",
        "If nothing moves by tomorrow, reply to the confirmation email.",
    ),
    (
        "Will do. And the confirmation goes to the same address?",
        "Same email, yes — the one we checked at the start.",
    ),
    (
        "Good. I have had confirmations go astray before.",
        "I will make sure this one is sent to the address on the account.",
    ),
)


def _turns(facts: Facts, variant: int) -> tuple[str, ...]:
    """One conversation. The fact-bearing sentences keep stable markers on purpose.

    This is a drill about what to keep, not about parsing English. Every fact is stated with a
    phrase a rule can find (`my spending limit`, `allergic to`, `the postcode is`), and the
    difficulty is in the budget and the corrections, not in the extraction.
    """
    return (
        "Customer: " + OPENINGS[variant % len(OPENINGS)].format(name=facts.name),
        "Assistant: " + GREETINGS[variant % len(GREETINGS)].format(first=facts.first),
        "Customer: " + PROBLEMS[variant % len(PROBLEMS)],
        "Assistant: Let me pull the order up. What's the email on the account?",
        f"Customer: It's {facts.email}.",
        "Assistant: Got it. And the order number?",
        f"Customer: It's {facts.order}. I'm on the {facts.plan} plan, if that matters.",
        f"Assistant: It does — {facts.plan} includes the priority queue.",
        "Customer: " + FILLERS[0][0],
        "Assistant: " + FILLERS[0][1],
        "Assistant: I can see the label was created. The courier has not scanned the parcel yet.",
        f"Customer: The address is 14 Bellamy Road, {facts.postcode_old}, by the way. "
        "Nothing has changed there.",
        "Assistant: Thank you. I have the address on file.",
        f"Customer: One thing for the delivery note: I'm allergic to {facts.allergy}, "
        "so nothing from that aisle.",
        f"Assistant: Noted. I will put {facts.allergy} on the handling instructions.",
        "Customer: " + FILLERS[1][0],
        "Assistant: " + FILLERS[1][1],
        f"Customer: While we're here — what's my spending limit? I thought it was £{facts.budget}.",
        f"Assistant: Yes, £{facts.budget} per order on your plan.",
        "Customer: Good, because the replacement might come close to that.",
        "Assistant: It should not. The replacement is covered.",
        f"Customer: The delivery is booked for {facts.date_old}, between {facts.window}. "
        "Can you keep that slot?",
        f"Assistant: {facts.date_old} is still showing as booked, and the two-hour window stands.",
        "Customer: " + FILLERS[2][0],
        "Assistant: " + FILLERS[2][1],
        "Customer: " + FILLERS[3][0],
        "Assistant: " + FILLERS[3][1],
        f"Customer: Actually — I moved last month. The postcode is {facts.postcode_new}, "
        f"not {facts.postcode_old}. Everything else is the same.",
        # The confirmation deliberately does not repeat the value: if it did, the new postcode
        # would be the last mention and "take the last match" would accidentally work.
        "Assistant: Updated. I have changed it on the account.",
        "Customer: " + FILLERS[4][0],
        "Assistant: " + FILLERS[4][1],
        "Assistant: Anything else on the delivery?",
        f"Customer: One correction: make it {facts.date_new}, not the {facts.old_day}.",
        f"Assistant: Moved to {facts.date_new}. The slot time is unchanged.",
        "Customer: " + FILLERS[5][0],
        "Assistant: " + FILLERS[5][1],
        "Customer: " + FILLERS[5][0],
        "Assistant: " + FILLERS[5][1],
        "Customer: " + FILLERS[5][0],
        "Assistant: " + FILLERS[5][1],
        "Customer: " + FILLERS[5][0],
        "Assistant: " + FILLERS[5][1],
        "Customer: " + FILLERS[5][0],
        "Assistant: " + FILLERS[5][1],
        "Customer: " + FILLERS[5][0],
        "Assistant: " + FILLERS[5][1],
        "Customer: " + FILLERS[5][0],
        "Assistant: " + FILLERS[5][1],
        "Customer: " + FILLERS[5][0],
        "Assistant: " + FILLERS[5][1],
        f"Customer: Before I go: the complaints reference is {facts.reference}. "
        "Can you put that on the file?",
        f"Assistant: Added. {facts.reference} is on the case.",
        f"Customer: And the buzzer is broken, so leave it with {facts.recipient} "
        f"and the gate code is {facts.gate}.",
        "Assistant: I will add that to the courier notes.",
        f"Customer: Great. I tried {facts.tried} first, by the way — it went in circles.",
        "Assistant: I'm sorry about that. The case is logged now.",
        "Customer: Is there anything you need from me?",
        "Assistant: No — I will email a confirmation once the courier re-scans it.",
        "Customer: Thanks for the help.",
        "Assistant: Any time.",
    )


@dataclass(frozen=True)
class Probe:
    id: str
    slot: str
    question: str
    accept: tuple[str, ...]
    category: str
    stale: tuple[str, ...] = ()
    naive_fails: str = ""  # "first", "last" or "both": which naive extraction rule is wrong


@dataclass(frozen=True)
class Conversation:
    id: str
    facts: Facts
    turns: tuple[str, ...]
    probes: tuple[Probe, ...]

    @property
    def transcript(self) -> str:
        return "\n".join(self.turns)


def _probes(conversation_id: str, facts: Facts) -> tuple[Probe, ...]:
    v = facts.values
    probes = (
        Probe(f"{conversation_id}-name", "name", "What name is on the account?", (v["name"],), "early"),
        Probe(f"{conversation_id}-email", "email", "Which email is on the account?", (v["email"],), "early"),
        Probe(f"{conversation_id}-order", "order", "What is the order number?", (v["order"],), "early"),
        Probe(f"{conversation_id}-plan", "plan", "Which plan is the customer on?", (v["plan"],), "early"),
        Probe(
            f"{conversation_id}-allergy", "allergy",
            "What must the courier keep out of the delivery?",
            (v["allergy"],), "constraint",
        ),
        Probe(
            f"{conversation_id}-budget", "budget",
            "What is the spending limit per order?",
            (v["budget"],), "constraint",
        ),
        Probe(
            f"{conversation_id}-window", "window",
            "What time window is the delivery booked into?",
            (v["window"],), "constraint",
        ),
        Probe(
            f"{conversation_id}-postcode", "postcode",
            "What postcode should the courier use?",
            (facts.postcode_new,), "corrected", stale=(facts.postcode_old,),
            naive_fails="both",
        ),
        Probe(
            f"{conversation_id}-date", "date",
            "What day is the delivery booked for?",
            (facts.date_new,), "corrected", stale=(facts.date_old,),
            naive_fails="first",
        ),
        Probe(
            f"{conversation_id}-reference", "reference",
            "What is the complaints reference?",
            (v["reference"],), "late",
        ),
        Probe(
            f"{conversation_id}-recipient", "recipient",
            "Who should the parcel be left with?",
            (v["recipient"],), "late",
        ),
        Probe(
            f"{conversation_id}-gate", "gate",
            "What is the gate code?",
            (v["gate"],), "late",
        ),
        # Deliberately outside the fact schema. No ledger of twelve labelled values anticipates
        # it, which is the price of deciding in advance what matters.
        Probe(
            f"{conversation_id}-tried", "unstructured",
            "What had the customer already tried before calling?",
            (v["tried"],), "unstructured",
        ),
    )
    # Probe order must not hint at where the fact lives, so it is rotated per conversation.
    shift = int(hashlib.sha256(conversation_id.encode()).hexdigest()[:4], 16) % len(probes)
    return probes[shift:] + probes[:shift]


def build(seed: int = 2027) -> list[Conversation]:
    conversations = []
    for index, facts in enumerate(FACTS):
        conversation_id = f"c{index + 1}"
        conversations.append(
            Conversation(
                id=conversation_id,
                facts=facts,
                turns=_turns(facts, index),
                probes=_probes(conversation_id, facts),
            )
        )
    return conversations


# -- the model --------------------------------------------------------------


def _unit(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:13], 16) / float(16**13)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[,£$]", "", text.casefold())).strip()


def _contains(haystack: str, phrase: str) -> bool:
    """Whole-token containment, so `nuts` does not match inside `peanuts`."""
    return re.search(r"(?<!\w)" + re.escape(_norm(phrase)) + r"(?!\w)", haystack) is not None


class MemoryBudgetExceeded(RuntimeError):
    """Raised when the memory handed to `answer` is over the budget. A crash, scored as one."""


@dataclass
class Summary:
    text: str
    tokens_in: int
    tokens_kept: int

    @property
    def ratio(self) -> float:
        return self.tokens_kept / max(1, self.tokens_in)


SALIENT = re.compile(r"\b(not|never|only|must|allergic|but)\b", re.I)
SENTENCE = re.compile(r"(?<=[.!?])\s+")


class MemoryModel:
    """Answers from the memory it is handed, and only from that.

    `summarise` is an extractive compressor: it scores sentences by generic cues (digits,
    capitalised words, negations), keeps the highest-scoring ones that fit, and — this is the
    part that matters — silently rewrites a number in a kept sentence at a rate that rises as
    the compression gets tighter. That is what a summariser under a hard budget does. It is not
    a bug in the drill; it is the failure mode the ledger policy exists to avoid.
    """

    name = "memory-model"
    COST_PER_CALL = 0.00002
    COST_PER_TOKEN = 0.0000005

    def __init__(self, conversations: list[Conversation]) -> None:
        self.by_id = {conversation.id: conversation for conversation in conversations}
        self._decoys: dict[str, list[str]] = {}
        for conversation in conversations:
            for slot, value in conversation.facts.values.items():
                self._decoys.setdefault(slot, [])
                if value not in self._decoys[slot]:
                    self._decoys[slot].append(value)
        self._decoys.setdefault("unstructured", ["the phone line", "the FAQ page", "email"])
        self.calls: list[dict] = []
        self.cost_usd = 0.0
        self.latencies: list[float] = []
        self.max_memory_tokens = 0
        self.reset()

    def reset(self) -> None:
        self.calls.clear()
        self.cost_usd = 0.0
        self.latencies.clear()
        self.max_memory_tokens = 0

    @property
    def n_calls(self) -> int:
        return len(self.calls)

    # -- memory construction ------------------------------------------------

    def summarise(self, text: str, max_tokens: int) -> Summary:
        sentences = [s.strip() for s in SENTENCE.split(text) if s.strip()]
        scored = []
        for index, sentence in enumerate(sentences):
            score = 0.0
            if re.search(r"\d", sentence):
                score += 2.0
            if SALIENT.search(sentence):
                score += 1.5
            score += 0.4 * len(re.findall(r"\b[A-Z][a-z]+\b", sentence))
            score -= 0.01 * count_tokens(sentence)
            scored.append((score, index, sentence))

        keep: list[tuple[int, str]] = []
        used = 0
        for _, index, sentence in sorted(scored, key=lambda row: (-row[0], row[1])):
            cost = count_tokens(sentence)
            if used + cost > max_tokens:
                continue
            keep.append((index, sentence))
            used += cost
        keep.sort()

        tokens_in = count_tokens(text)
        pressure = min(0.45, 0.9 * (1.0 - used / max(1, tokens_in)))
        kept_text = " ".join(self._corrupt(sentence, pressure) for _, sentence in keep)

        latency = 40.0 + tokens_in * 0.05
        self._record("summarise", tokens_in, used, latency)
        return Summary(text=kept_text, tokens_in=tokens_in, tokens_kept=used)

    @staticmethod
    def _corrupt(sentence: str, pressure: float) -> str:
        match = re.search(r"\d[\d,]*", sentence)
        if match is None:
            return sentence
        if _unit(sentence, "corrupt") >= pressure:
            return sentence
        digits = re.sub(r"\D", "", match.group(0))
        step = (1, 3, 4, 5, 6)[int(_unit(sentence, "step") * 5)]
        if len(digits) == 1:
            replacement = str((int(digits) + step) % 10)
        else:
            replacement = str(int(digits) + step)
        return sentence[: match.start()] + replacement + sentence[match.end() :]

    # -- answering ----------------------------------------------------------

    def answer(self, probe: Probe, memory: str) -> str:
        tokens = count_tokens(memory)
        self.max_memory_tokens = max(self.max_memory_tokens, tokens)
        if tokens > BUDGET_TOKENS:
            raise MemoryBudgetExceeded(
                f"memory is {tokens} tokens, budget is {BUDGET_TOKENS}"
            )

        haystack = _norm(memory)
        reply = None
        for phrase in probe.accept:
            if _contains(haystack, phrase):
                reply = phrase
                break
        if reply is None:
            for phrase in probe.stale:
                if _contains(haystack, phrase):
                    reply = phrase
                    break
        if reply is None:
            reply = self._decoy(probe) if _unit(probe.id, "confabulate") < CONFABULATE else "I don't know."

        latency = 90.0 + tokens * 0.2
        self._record("answer", tokens + count_tokens(probe.question), count_tokens(reply), latency)
        return reply

    def decoys_for(self, probe: Probe) -> list[str]:
        """Values the model may invent for this probe. Never the right one."""
        return [value for value in self._decoys.get(probe.slot, []) if value not in probe.accept]

    def _decoy(self, probe: Probe) -> str:
        pool = self.decoys_for(probe)
        if not pool:
            return "I don't know."
        return pool[int(_unit(probe.id, "decoy") * len(pool)) % len(pool)]

    def _record(self, kind: str, tokens_in: int, tokens_out: int, latency: float) -> None:
        cost = self.COST_PER_CALL + tokens_in * self.COST_PER_TOKEN
        self.cost_usd += cost
        self.latencies.append(latency)
        self.calls.append(
            {
                "kind": kind,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": cost,
                "latency_ms": latency,
            }
        )


def model(conversations: list[Conversation]) -> MemoryModel:
    return MemoryModel(conversations)
