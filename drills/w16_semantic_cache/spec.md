# w16 — The semantic cache

| | |
| --- | --- |
| **Goal** | Reuse an earlier answer when a new question means the same thing, without serving an answer to a different question. |
| **Outcome** | A cache policy that serves about three quarters of the traffic with fewer than 5% wrong answers. |
| **Target** | hit rate ≥ 68%, wrong hits ≤ 5%, under $0.40 of model calls |
| **Time** | 45 to 75 minutes |

## 1. Why this drill exists

Every support assistant is asked the same forty questions in different words, all day. A cache
keyed on exact text almost never hits. A cache keyed on embedding similarity hits often — and
sometimes serves the answer to a different question, which is worse than not caching at all.

The engineering question is not "should we cache". It is **where the threshold goes**, and that
question has no answer in the abstract. It has an answer once you say what a wrong answer costs
relative to a missed cache.

This drill is the same decision as the sufficiency gate in `triage` and the routing threshold in
`w08`: a similarity score, a budget for one kind of error, and a point on a curve.

## 2. What you are given

- `data.py`: eight days of traffic, 200 turns each. 40 intents, 5 phrasings each, embedded as
  48-dimensional points. Six pairs of intents sit at 0.96 similarity to each other: those are the
  trap pairs.
- `data.TRUTH`: intent labels, kept out of the items so your task cannot read the answer.
- `data.AnswerModel`: the model the cache exists to avoid calling. $0.0004 per call.
- `task.py`: a cache keyed on exact text. It never hits.

The embeddings are synthetic and `data.py` says so. A real encoder's errors are not Gaussian, so
the absolute numbers do not transfer to production. The decision does.

## 3. How to run it

```sh
python3 run.py --drill w16_semantic_cache
python3 run.py --drill w16_semantic_cache --task solutions/w16_reference.py
python3 -m unittest tests.test_drills -v
```

## 4. Background: the idea from first principles

A cache lookup is a classifier over pairs: *is this new question the same intent as that cached
one?* The score is cosine similarity. The threshold turns the score into a decision.

```
serve(turn) = argmax over cached c of cos(turn, c)   if that score >= threshold
            = call the model                         otherwise
```

Two errors, and they are not symmetric:

| error | what happens | cost |
| --- | --- | --- |
| false hit | the customer is told how to cancel a subscription when they asked about an order | a wrong answer, and a support ticket |
| miss | the model answers a question it has answered before | one call, $0.0004 |

The drill sets the ratio at **one wrong answer = 20 missed caches**, which is why the budget is
5% of turns. That ratio is a policy decision, and it is the only reason a single threshold can be
called correct.

**Why the trap pairs matter.** Six intent pairs sit at 0.96. Any threshold below 0.96 will
occasionally confuse them. That is not a bug in your code; it is a ceiling in the data, and it is
where the shape of the curve comes from.

## 5. The task, step by step

1. Run the starting policy. Note the hit rate (zero), the wrong hits (zero) and the cost (all of
   it).
2. Implement the lookup: for each turn, find the most similar cached embedding and serve it when
   the score clears your threshold.
3. Sweep the threshold on **days 1 to 6** and plot hit rate against wrong-hit rate.
4. Pick the threshold that keeps wrong hits inside the budget with the most hits. Write down the
   number you picked and what it would be if a wrong answer cost five times more.
5. Run the held-out days. The card reports them separately.

Return `{"served": [...]}` with one entry per turn: the id of the turn whose answer you reused,
or `None`.

## 6. How you are scored

| metric | weight |
| --- | --- |
| hit rate | the accuracy line, target 68% |
| wrong hits | hard gate: above 5%, the run scores zero |
| cost | cap $0.40 of model calls |
| crashes | must be zero |
| model calls | at least one per day, because a cache that answers nothing is not a cache |

A run that exceeds the wrong-hit budget scores zero rather than a reduced number. Serving the
wrong answer is not a partial success, and averaging it with a good hit rate would hide that.

## 7. Done when

- [ ] `python3 run.py --drill w16_semantic_cache --task solutions/w16_reference.py` reports TARGET MET
- [ ] the starting policy reports both a low hit rate and a cost over the cap
- [ ] you can state your threshold and the ratio of error costs that justifies it
- [ ] you have run the held-out days and reported them separately
- [ ] `python3 run.py --drill w16_semantic_cache --seed 11` also passes, if your policy is not
      tuned to one seed

## 8. Carry forward

The threshold is the same object as `triage`'s sufficiency gate and `w08`'s router. In all three,
the number comes from a cost ratio, not from the data alone.

Two things this drill does not do. It does not expire entries: a real cache needs a TTL, because
the answer to "where is my parcel" changes. And it does not handle the multi-turn case, where the
second question ("and the other one?") is only meaningful with the first. Both are real failures,
and both would need their own measurement.
