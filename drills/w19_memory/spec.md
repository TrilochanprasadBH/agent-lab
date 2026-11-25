# w19 — Memory under a fixed budget

| | |
| --- | --- |
| **Goal** | Answer questions about a long conversation from a memory that fits in 160 tokens. |
| **Outcome** | 100% of 78 probes retained, from 87 tokens per call, at $0.0052. |
| **Target** | retention ≥ 85%, 13 answer calls per conversation, under $0.020 |
| **Time** | 60 to 90 minutes |

## 1. Why this drill exists

Every assistant that is used for more than ten minutes hits the same wall: the conversation is
longer than the context the next call can afford. Something has to be left out, and the choice of
what to leave out is the whole design.

The default is to keep the most recent turns and drop the rest. It is easy to write, it is what
most chat windows do, and it is wrong in a specific way. In this corpus it retains **30.8%** of
what the customer will later be asked about, and it does not fail by staying silent: **26.9% of
its answers are wrong values the customer never gave**. A remembered "I don't know" is annoying.
A remembered postcode from the previous address is a parcel delivered to a stranger.

The drill measures three policies against each other on the same conversations, the same budget,
and the same 78 probes:

- **truncate** — keep the last turns that fit
- **summary** — compress the older turns with an extractive summariser
- **ledger** — extract the facts, label them, drop the prose
- **ledger + window** — the ledger plus the last six turns for continuity

The answer is not "summarise harder". It is that **retention and compression are different
operations**, and a summariser is a lossy compressor with no idea which sentence will be asked
about.

## 2. What you are given

- `data.py`: 6 support conversations, 60 turns and about 650 tokens each, with 13 probes.
- `data.BUDGET_TOKENS = 160`: the memory handed to each answer call.
- `data.MemoryModel.summarise(text, max_tokens)`: an extractive compressor that keeps the
  highest-scoring sentences and, under pressure, **silently rewrites a number**.
- `data.MemoryModel.answer(probe, memory)`: answers from that memory only. If the value is
  missing it invents a plausible one 40% of the time and says "I don't know" the rest.
- `task.py`: the truncation baseline.
- `sweep.py`: all four policies and the correction-rule comparison. Every number here comes
  from it.
- `check_labels.py`: verifies the corpus has the properties this lesson claims.

The conversations are authored, not vendored, because the exercise depends on exact, labelled
ambiguities that no public corpus contains: a fact stated once, corrected later with the old
value quoted inside the correction, and never repeated. `check_labels.py` verifies every value,
every trap, and the shape of the truncation window.

## 3. How to run it

```sh
python3 drills/w19_memory/check_labels.py
python3 drills/w19_memory/sweep.py
python3 run.py --drill w19_memory
python3 run.py --drill w19_memory --task solutions/w19_reference.py
```

## 4. Background: what each policy keeps, and what it costs

| policy | retained | early | constraint | corrected | late | other | wrong | abstain | memory | cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| truncate | 30.8% | 0% | 0% | 0% | 100% | 100% | 26.9% | 42.3% | 160 | $0.0080 |
| summary | 56.4% | 21% | 44% | 67% | 94% | 100% | 19.2% | 24.4% | 160 | $0.0099 |
| ledger | 92.3% | 100% | 100% | 100% | 100% | 0% | 1.3% | 6.4% | 32 | $0.0030 |
| ledger + window | **100%** | 100% | 100% | 100% | 100% | 100% | 0.0% | 0.0% | 87 | $0.0052 |

`memory` is the largest memory sent to a single answer call, in tokens. The budget is 160.

**Truncation is a specialist.** It is perfect on what just happened and blind to everything
before it. The four groups are not equally weighted by accident: `late` and `other` are inside
the window, `early`, `constraint` and `corrected` are not. That is why it scores 30.8% and not
zero — the last turns are a real memory, just a very short one.

**Summarising doubles it and still loses half.** The summary keeps 106 tokens out of 596 and
retains 56.4%. Here is what it produced for one conversation, verbatim:

```
Customer: It's A-4472. Customer: The address is 14 Bellamy Road, SW1A 1AA, by the way.
Assistant: Noted. Assistant: Yes, £1206 per order on your plan. ...
Customer: The delivery is booked for 17 March, between 9 and 11.
Assistant: 13 March is still showing as booked ... Moved to 17 March.
... The postcode is SW1A 2AA, not SW1A 1AA.
Customer: One correction: make it 14 March, not the 12th.
```

The order is `A-4472`, not `A-4471`. The budget is `£1206`, not `£1,200`. The delivery moved to
`17 March` in two sentences that were originally about the 12th and the 14th. Every one of those
numbers is wrong and every one reads like a fact. The compression ratio is 0.18, and the
summariser's corruption pressure rises as the budget tightens — at 0.18 it rewrites a number in
roughly half the sentences it keeps.

**The ledger keeps all twelve facts in 32 tokens.** 650 tokens to 32, and the probes come back
clean, because the facts are short and the prose around them is not. This is the drill's central
arithmetic: **a fact is cheaper than the sentence that states it, by an order of magnitude.** The
ledger is not a summary. Nothing is paraphrased and nothing is lost, because nothing else is
kept.

**The ledger alone still fails one probe, and that is the point.** The `other` column is the
customer saying, near the end, that they tried the chat first. No schema of twelve labelled
values anticipates it, and the ledger scores 0% on it while the *truncation baseline* scores
100%. Adding the last six turns back costs 55 tokens and fixes it. That is what the window is
for: **not the facts you knew to extract, the context you did not know to ask for.**

### The correction rule is worth 15 points on its own

Both corrected values are stated, then corrected. The obvious implementations get them wrong:

| ledger rule | retained | corrected | wrong |
| --- | --- | --- | --- |
| take the first match | 84.6% | 0% | 15.4% |
| take the last match | 92.3% | 50% | 7.7% |
| skip a negated mention, then take the last | **100%** | 100% | 0% |

"Take the first match" keeps the original postcode and the original date. "Take the last match"
does better on the date and still fails the postcode, because the correction quotes the old value
*after* the new one: `the postcode is SW1A 2AA, not SW1A 1AA`. The rule that works is the one a
person applies when reading — a mention that is being rejected is not a mention — and it is the
difference between 84.6% and 100%.

## 5. The task, step by step

1. Run the baseline. Note that it is perfect on `late` and `unstructured` and zero everywhere
   else, and that 21 of its 78 answers are invented rather than refused.
2. Run `sweep.py`. Compare the `summary` and `ledger` rows: same budget, same probes, 35 points
   apart, and the ledger uses a fifth of the memory.
3. Write extraction for the twelve facts. Use stable markers — this is a drill about what to
   keep, not about parsing English.
4. Handle the corrections. Read the sentence that corrects: it names the new value first and the
   old value second, and the old value is negated. Decide what your extractor does with a
   negated mention.
5. Add the last six turns. Check what it buys: one probe, 55 tokens.
6. Run the reference, then read `check_labels.py` and see which invariant would catch you if you
   broke the corpus.

Return one answer string per probe, in the order the conversation gives them.

## 6. How you are scored

| metric | weight |
| --- | --- |
| retained | the accuracy line, target 85% |
| wrong answers | reported separately; a wrong value is not a miss |
| abstained | reported separately |
| memory | hard limit: over 160 tokens raises, and the conversation scores zero |
| calls | at least one answer call per probe |
| cost | cap $0.020 of model calls |

The wrong/abstain split is the reason the baseline is worse than its 30.8% suggests. Truncation
does not fail quietly — 21 of its answers are confident and false. Any policy that raises
retention by making the model more willing to guess is moving the number in the wrong direction,
which is why the two rates are on the card next to the score.

## 7. Done when

- [ ] `python3 run.py --drill w19_memory --task solutions/w19_reference.py` reports TARGET MET
- [ ] you can explain why truncation scores 30.8% and not 0% or 50%
- [ ] you can state the three facts the summary corrupted in the excerpt, and why it corrupted
      them
- [ ] you can say what the ledger costs you, and which column shows it
- [ ] you can explain why "take the last match" still fails on the postcode
- [ ] `check_labels.py` passes, and you can say what it would catch

## 8. Carry forward

The ledger's 92.3% is not free. It is 92.3% **on a probe set whose schema you were shown**. The
extraction knows there is a postcode because the question asks about a postcode. In production
the schema is your guess about what users will ask, and the `other` column is the measured cost
of that guess: the one detail nobody schematised, kept for free by the dumbest policy in the
table. The honest design is both — facts for what you can enumerate, a window for what you
cannot.

What this drill does not model: retrieval over a long-term store (everything here is one
conversation, compacted once), forgetting curves, a memory the user can inspect and edit, and
the privacy question of what a summary should not retain. That last one is `w17`'s problem
applied to memory rather than to prompts, and `triage` stage 05 is where it becomes real: a
summary that keeps a card number keeps it in every subsequent call.

The other limit is that the reader here is a lookup. A real model paraphrases, and a paraphrase
can be right for the wrong reason — it may recover a fact from context that the memory does not
contain. That would make every policy in the table look better and would make the difference
between them smaller. The drill measures the memory, not the model, and it says so.
