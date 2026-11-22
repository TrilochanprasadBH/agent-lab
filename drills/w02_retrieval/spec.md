# Drill 02 — Finding the right document

| | |
| --- | --- |
| **Goal** | Build a retrieval function that returns the document that answers a question. |
| **Outcome** | A ranked search over 40 documents that places the correct document in the top three for 88% of 30 questions. |
| **Target** | 88% mean of recall@3 and first-hit. |
| **Time** | 60 to 90 minutes. |

---

## 1. Why this drill exists

Before a model can answer a question, something has to put the right document in
front of it. That something is retrieval.

When an AI system gives a confident wrong answer, the usual cause is that the
correct document was never retrieved. You cannot recover from a missing document by
writing a better prompt, because the model never saw it.

This drill builds retrieval from scratch, with no vector database and no embedding
model, so you can see exactly what the ranking is doing.

## 2. What you are given

- `data.py`: 40 internal runbooks (title plus a short body) and 30 questions.
- Each question has a known correct document, called the gold document.
- `data.py` also contains an alias table: pairs of phrases that mean the same thing
  in this domain.
- `task.py`: the file you edit. It counts shared words.

## 3. How to run it

```sh
python3 run.py --drill w02_retrieval
python3 run.py --drill w02_retrieval --failures 10
python3 run.py --drill w02_retrieval --task solutions/w02_reference.py
```

## 4. Background: the idea from first principles

**The problem.** You have 40 documents and a question. You want the documents most
likely to contain the answer, ordered best first.

**The naive method.** Split the question into words. Count how many of those words
appear in each document. Rank by the count.

This is where everyone starts, and it fails for four separate reasons. Each reason
has a specific fix.

**Problem 1: common words dominate.**

The word "cache" appears in a dozen documents. The word "idempotency" appears in
one. Matching "cache" tells you almost nothing; matching "idempotency" tells you
almost everything.

The fix is to weight each term by how rare it is. This is inverse document
frequency:

```
idf(term) = log((N + 1) / (df + 1)) + 1
```

where `N` is the number of documents and `df` is the number containing the term. A
term in every document gets a weight near 1. A term in one document gets a much
higher weight.

The intuition: a term that appears everywhere cannot distinguish anything. A term
that appears once is strong evidence.

**Problem 2: word forms do not match.**

The question says "evicting". The document says "evicted". A character-by-character
comparison sees two different words.

The fix is stemming: reduce each word to a common stem by removing common endings
(`-ing`, `-ed`, `-es`, `-s`, `-ies` → `y`). This is crude and occasionally wrong,
and it is good enough.

One caution: naive stemming over-strips. Removing `-es` from "certificates" gives
"certificat", which no longer matches "certificate". Only strip `-es` when the stem
ends in `s`, `x`, `z`, `ch`, or `sh`.

**Problem 3: the question uses different words than the document.**

A user writes "sign-in". The document says "SAML" and "identity provider". A user
writes "money back". The document says "refund".

No amount of counting closes this gap, because the words are genuinely different.

The fix is an alias table: a mapping from a term to other terms that mean the same
thing in your domain. This is not a hack; every production retrieval system has one,
because domain vocabulary is always inconsistent.

Two details matter:

- Match the alias table against the **raw question text**, before stemming.
  Multi-word aliases such as "money back" are destroyed by tokenisation.
- Give alias terms slightly less weight than the original term. A synonym is
  weaker evidence than the exact word.

**Problem 4: position is ignored.**

The title of a document is the author's summary of what it is about. A term that
appears in the title is more informative than the same term in the fourth
paragraph.

The fix is a title boost: add extra score when a matching term also appears in the
title. An exact phrase match deserves a smaller bonus for the same reason.

**The metrics.** Two numbers matter.

- **recall@3**: of the questions where a correct document exists, the fraction
  where it appears in your top three.
- **first-hit**: the fraction where it is ranked first.

Recall@3 measures whether you found it. First-hit measures whether you ranked it
well enough that the model reads it first. Both matter; a system that returns the
right document third is wasting context budget.

## 5. The task, step by step

1. Run the starting code. Note the gap between recall@3 and first-hit.
2. Build a tokeniser: lowercase, split on non-alphanumeric, drop stop words.
3. Add stemming to the tokeniser.
4. Build an inverted index over the 40 documents and compute `idf` for every term.
5. Score each document as the sum of `idf × term frequency` for matching terms.
6. Add alias expansion, matched on raw text with word boundaries.
7. Add the title boost and the phrase bonus.
8. Sort by score, break ties by document id, return the top three.

## 6. How you are scored

For each of the 30 questions, your function returns a list of document ids.

- `recall@3` is the fraction where the gold document is among the first three.
- `first-hit` is the fraction where the gold document is first.
- `accuracy` is the mean of those two numbers.

The drill passes at 88% or better.

Retrieval needs no model calls, so the cost cap is not binding here. The score
measures the index you built.

## 7. Done when

- [ ] `python3 run.py --drill w02_retrieval` reports TARGET MET
- [ ] recall@3 is 100% or close to it
- [ ] first-hit is above 85%
- [ ] you can explain which of the four fixes bought the most points
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

Ranking is not counting. Four independent improvements, in order of value:

1. weight terms by rarity
2. normalise word forms
3. expand vocabulary with a domain alias table
4. reward titles and exact phrases

Before reaching for a vector database, check whether these four get you there. On a
corpus of a few thousand well-titled documents, they often do.
