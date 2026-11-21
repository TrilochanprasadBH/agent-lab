# Drill 02 — retrieval from scratch

**Target:** 88% mean of recall@3 and first-hit, over 30 questions.

```
python3 run.py --drill w02_retrieval
```

You edit `task.py`. The corpus is 40 internal runbooks; the questions are asked in
different words than the documents use.

## Why the baseline fails

`solutions/../task.py` counts shared words. It sounds reasonable and it scores
about 72%, because:

- **Common words dominate.** "cache", "service" and "request" appear in a dozen
  documents. A term present in thirty documents carries almost no information,
  and unweighted counting cannot say so.
- **Morphology fragments your terms.** `evicting` ≠ `evicted` ≠ `evict`, so a
  query misses a document that says exactly what it means.
- **Query language is not document language.** People say "sign-in", the docs say
  "SAML" and "identity provider". People say "money back", the docs say "refund".
  No amount of counting closes this gap — only an alias table does.
- **Everything is one flat bag.** The title is the author telling you what the
  document is about. The baseline ignores it.

## The four moves

1. **IDF weighting.** Weight each term by rarity: `log((N+1)/(df+1)) + 1`.
2. **Stemming.** Strip `-ing`, `-ed`, `-es`, `-ies` so variants collapse.
3. **Alias expansion, on raw text.** Match the alias table against the *query
   string before stemming*. `"money back"` has to be matched as a phrase, or it
   is gone by the time you tokenize.
4. **Title and phrase boosts.** A term in the title is worth more than the same
   term buried in paragraph four.

## Done looks like

- [ ] `python3 run.py --drill w02_retrieval` reports TARGET MET
- [ ] you can name which of the four moves bought the most points
- [ ] `first-hit` is above 85%, not just `recall@3` — getting the right document
      into the top three is easier than ranking it first, and only one of those
      is good enough to put in a prompt

## Why this matters for agents

Every RAG system you build is this drill plus an API. When an agent gives a
confident wrong answer, the cause is more often retrieval than reasoning: the
right document never entered the window. You cannot prompt your way out of a
missing document.
