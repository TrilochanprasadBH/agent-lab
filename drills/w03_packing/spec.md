# Drill 03 — Fitting evidence into a budget

| | |
| --- | --- |
| **Goal** | Assemble the documents a question needs, inside a fixed token budget. |
| **Outcome** | A packing function that includes the required evidence for 90% of 18 questions, never exceeding 120 words. |
| **Target** | 90% evidence coverage, every pack inside the budget. |
| **Time** | 45 to 75 minutes. |

---

## 1. Why this drill exists

A context window is finite. You cannot send every document. So every request forces
a decision: which documents go in, and in what order.

This is a different problem from retrieval. Retrieval asks *which document is most
relevant*. Packing asks *is the evidence I need actually inside the window*. Those
have different answers, and the difference shows up as soon as the budget is tight.

## 2. What you are given

- The same 40 runbooks as drill 02.
- `data.py`: 18 questions. Each requires evidence from one or two specific
  documents, identified by a short phrase that must appear in the packed text.
  The budget is 120 whitespace-separated words.
- `task.py`: the file you edit. It appends documents in corpus order until the
  budget runs out.

## 3. How to run it

```sh
python3 run.py --drill w03_packing
python3 run.py --drill w03_packing --failures 5
python3 run.py --drill w03_packing --task solutions/w03_reference.py
```

## 4. Background: the idea from first principles

**What a pack is.** A single string, built from some of the 40 documents, that will
be placed in the model's context window along with the question. Your function
returns that string.

**What the budget means.** The model can only consider a limited number of tokens.
Here, the limit is measured in words: 120. If you exceed it, the pack is invalid even
if it contains the right evidence.

**Why the naive approach fails.** Taking documents in corpus order ignores the
question entirely. It is the equivalent of answering "which chapters of this book
are relevant?" with "the first four".

**Why relevance alone is not enough.** Here is the part that makes this drill
different from drill 02.

Suppose three documents are all highly relevant to the question. Suppose further
that all three discuss the same half of the question, and none discusses the other
half. A ranking function would cheerfully return all three, and the pack would be
missing the one piece of evidence that mattered.

Relevance ranks documents independently. A budget forces them to share space, so
their *coverage* matters more than their individual scores.

**The two-part fix.**

First, score documents against the question with `idf`, as in drill 02. This orders
them sensibly.

Second, when you select, prefer the documents that are relevant *and short*, because
cost is paid in tokens. A document that answers half the question in 30 words beats
a document that repeats the first one in 80.

**Sentence-level packing.** Documents are made of sentences. If a document does not
fit whole, adding part of it is better than dropping it, but only if you cut at a
sentence boundary. Cutting mid-sentence usually removes the clause that carried the
answer.

**Do not spend budget on a header with nothing behind it.** A title followed by no
body is a pointer, not evidence.

**Multi-document questions.** About half of these questions need two documents. If
you pack only the single best document, you have a ceiling of about 50% no matter
how good your ranking is. Read the question as asking for a set, not a winner.

## 5. The task, step by step

1. Run the starting code. Coverage will be low and budget compliance perfect.
2. Tokenise the question, drop stop words, stem.
3. Expand the question with the alias table from drill 02.
4. Score each document with `idf` against the expanded question, plus a title boost.
5. Select by score per token, not by score alone.
6. When a document does not fit whole, add sentences until the next one does not fit.
7. Stop when the budget is nearly full, leaving a token of slack.
8. Never return a document header with no body.

## 6. How you are scored

For each question, the harness checks two things about your returned string:

1. Does it contain every required phrase for that question?
2. Is its word count at most 120?

`evidence coverage` is the fraction of questions where both are true. A pack that
contains the evidence but exceeds the budget counts as a failure.

`accuracy` equals `evidence coverage`. The drill passes at 90% or better.

The note on the scorecard reports how many packs stayed inside the budget. If that
number is below 18, you have a budget bug even if your coverage looks fine.

## 7. Done when

- [ ] `python3 run.py --drill w03_packing` reports TARGET MET
- [ ] the budget note says every pack stayed inside 120 words
- [ ] you can name a question that needs two documents and show both in your pack
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

A context window is a budget, and budgets turn ranking into covering.

- Score for relevance, but select for coverage per token.
- Cut at sentence boundaries.
- Treat multi-document questions as a set-cover problem, not a best-match problem.
