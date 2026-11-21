# Drill 03 — context packing under a budget

**Target:** 90% of questions with the evidence present, inside 120 tokens.

```
python3 run.py --drill w03_packing
```

You edit `task.py` and return one string.

## The shift this drill forces

Drill 2 was ranking: which document is *most* relevant? This is covering: is the
evidence I need *inside the window*? Those diverge the moment the budget is tight.

Three relevant documents can miss the answer completely, because all three cover
the same half of the question. You cannot see that from a relevance score. You see
it from a coverage check.

## What the baseline does

It walks the corpus in order and appends documents until the budget is full. It
scores **11%**. It is not being lazy — this is what "just put the docs in the
prompt" actually does when there are more docs than fit.

## The moves

1. **Rank by IDF, not by shared words.** "the", "how", and the half-dozen product
   words in every document carry no signal.
2. **Budget per block, not globally.** Decide what fits *before* you concatenate,
   or you will cut mid-sentence and lose the clause that mattered.
3. **Truncate at sentence boundaries.** A document ending in "unless the" is worse
   than a shorter document that ends cleanly.
4. **Never spend tokens on a header with no evidence behind it.** A title alone is
   a pointer, not a fact.
5. **Know which questions need two documents.** Roughly half of these do. Packing
   the single best document is a 50% ceiling.

## Done looks like

- [ ] TARGET MET on the default run
- [ ] every pack is under 120 tokens — check the note, not just the score
- [ ] you can explain why a document that ranked second was still worth its tokens

## The uncomfortable part

An agent with a full context window and the wrong document behaves exactly like an
agent that is bad at reasoning. The failure looks like a thinking problem and is
almost always a selection problem. This drill is where you learn to tell them
apart.
