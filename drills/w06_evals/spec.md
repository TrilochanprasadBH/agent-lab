# Drill 06 — evals that resist overfitting

**Target:** 90% agreement with human labels on a **held-out** test set.

```
python3 run.py --drill w06_evals
```

You edit `task.py`. Implement `grade(reply, model) -> bool`.

## The trap, stated plainly

The train set has 140 labelled replies. The test set has 70, and you never see the
labels.

In the train split, every good reply opens with "Thanks for…" and runs long. Both
are true. Both are *artifacts of one writing team*, and neither survives the split:

| heuristic | train | test |
|---|---|---|
| long reply = good | ~70% | 50% |
| starts with "Thanks" | ~85% | 50% |
| the rubric below | ~95% | ~100% |

A grader built on length looks like progress for as long as you only measure on
the data you looked at. That is exactly how eval work fails in practice, and it is
why "our evals pass" is a sentence that should always be followed by "on what".

## What a reply actually has to do

1. **No placeholders.** `[NAME]`, `TODO`, `{{…}}` mean nobody finished it.
2. **No policy violation.** Refunds are 30 days. A polite reply promising 90 days
   is wrong.
3. **No empty commitment.** "I'll look into it", "get back to you", "as soon as
   possible", "guaranteed" — all ways of saying nothing, or of overpromising.
4. **Concrete and on topic.** A number (a reference, a timeframe) *and* an answer
   to the question that was actually asked.

Notice that every one of these is a claim about the artifact, not a statistic about
the split. That is what makes it survive contact with new data.

## Done looks like

- [ ] TARGET MET on the hidden split
- [ ] your grader does not use `len()` or the word "thanks"
- [ ] you computed your score on the *train* split too, and know the gap
- [ ] you can state the rubric in four sentences without looking at your code

## The rule to take forward

An eval is a model of quality. A model fitted to one sample of writers is not a
model of quality, no matter how well it scores on that sample.
