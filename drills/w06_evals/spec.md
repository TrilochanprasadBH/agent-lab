# Drill 06 — Writing an eval that generalises

| | |
| --- | --- |
| **Goal** | Write a grader for support replies that agrees with human labels on data you have not seen. |
| **Outcome** | A `grade` function scoring 90% agreement on a held-out set of 70 replies, without using any feature that exists only in the training sample. |
| **Target** | 90% agreement on the held-out split. |
| **Time** | 60 to 90 minutes. |

---

## 1. Why this drill exists

There are two ways to measure output quality. You can check it against a known
correct answer, which works when answers are exact. Or you can define a rule for
what "good" means, which is what you need for open-ended text.

Writing that rule is the skill. Writing a rule that scores well on the examples you
looked at, and badly on everything else, is the failure this drill teaches you to
avoid.

## 2. What you are given

- `data.py`: 210 support replies, each labelled good or bad by a human, split into
  two sets.
  - **train**: 140 replies, labels visible to you.
  - **test**: 70 replies, labels hidden. This is what you are scored on.
- Each reply includes the customer's question, so the grader can check whether the
  reply addressed it.
- `task.py`: the file you edit. It currently returns `True` for replies over 150
  characters.

To inspect the training data:

```sh
python3 -c "from drills.w06_evals.data import train_examples; \
[print(label, '|', r.text) for r, label in train_examples()[:10]]"
```

## 3. How to run it

```sh
python3 run.py --drill w06_evals
python3 run.py --drill w06_evals --failures 10
python3 run.py --drill w06_evals --task solutions/w06_reference.py
```

## 4. Background: the idea from first principles

**What a label is.** A human decision about one example: this reply is good, that
one is not.

**What a split is.** You take your labelled examples and divide them. You develop
against one part, the training set, and measure against the other, the test set.
The test labels are hidden from you during development.

**Why the split exists.** Because any rule you design while looking at examples will
fit those examples. That is not a moral failing, it is arithmetic: with enough
features available, you can always separate a finite set perfectly, including its
random noise.

The test set answers one question: does your rule work on data you did not look at?

**The trap in this particular train set.** Two properties of the training data
correlate with the label, and neither is a cause of quality:

- Every good training reply opens with "Thanks for…".
- Every good training reply is longer than 150 characters.

Both are true because one writing team produced that split. In the test set, good
replies are short and open differently.

So the baseline, "long means good", scores about 70% on train and 50% on test. A
grader built on "starts with Thanks" scores about 85% on train and 50% on test.

This is what overfitting looks like from the inside: the training number goes up and
means nothing.

**What a good rule looks like.** It states a property of the artifact, not a
statistic of the sample. Four useful checks for this data:

1. **No placeholders.** `[NAME]`, `TODO`, `{{...}}` mean nobody finished the reply.
   That is true of any reply, in any sample.
2. **No policy violation.** Refunds are available for 30 days in this company. A
   reply promising 90 days is wrong, however politely it is written.
3. **No empty commitment.** "I'll look into it", "get back to you", "as soon as
   possible", "guaranteed" are all ways of saying nothing, or of overpromising.
   Notice these are language patterns, not lengths.
4. **Concrete and on topic.** There must be a specific detail (a reference number or
   a timeframe) and the reply must address the question that was asked. You have the
   question, so you can check.

**Why "on topic" needs a mention.** A reply can be well written, contain a number,
and answer a completely different question. That is a real failure mode in support
systems, and only a check against the question catches it.

**Precision and recall, in case you want to reason about your rule.** If your
grader says "good" for 40 replies and 35 of them really are good, that is high
precision. If there are 35 genuinely good replies in the set and you found all of
them, that is full recall. The score here is plain agreement, but knowing which kind
of error you are making tells you what to fix.

## 5. The task, step by step

1. Read at least 20 training examples, both labels.
2. Write down, in your own words, what the bad ones have in common. Look for
   properties, not lengths.
3. Write `grade(reply, model)` returning a boolean.
4. Do not use `len()`. Do not use the word "thanks". Increase the score by removing
   those two crutches, not by adding them.
5. Run it. Read the false positives and false negatives.
6. Adjust the rule, not the threshold.

## 6. How you are scored

`agreement` is the fraction of the 70 held-out replies where your grader returns the
same boolean as the human label.

The drill passes at 90% or better.

The training score is not measured and not shown. That is deliberate: the training
score is the one that lies to you.

## 7. Done when

- [ ] `python3 run.py --drill w06_evals` reports TARGET MET
- [ ] your grader does not reference reply length
- [ ] your grader does not reference the word "thanks"
- [ ] you can state your rule in four sentences without reading your code
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

An eval is a model of quality. A model fitted to one sample of writers is not a
model of quality, however well it scores on that sample.

Before trusting any eval, ask: what does this rule check about the artifact, and
what does it only check about my sample?
