# Drill 08 — Hitting a quality target under a cost cap

| | |
| --- | --- |
| **Goal** | Send each question to a model tier that can answer it, and no more than that. |
| **Outcome** | A routing function that answers 92% of 40 questions correctly for under $0.030, using two tiers with a 7.5x price difference. |
| **Target** | 92% correct, total cost at or below $0.030. |
| **Time** | 45 to 60 minutes. |

---

## 1. Why this drill exists

A correct answer that costs four times what it needed to is not a good result. In
production, cost per request is a design constraint like any other, and the
cheapest way to meet it is usually to stop using the most expensive model for work
that does not need it.

This drill gives you two tiers and a budget that makes using only the expensive one
impossible.

## 2. What you are given

- `data.py`: 40 questions, 25 easy and 15 hard.
- A model with two tiers. You choose the tier by writing it into the prompt:

| tier | cost per call | behaviour |
| --- | --- | --- |
| cheap | $0.0002 | correct on easy questions, wrong on hard ones |
| strong | $0.0015 | correct on everything |

- `task.py`: the file you edit. It sends everything to the strong tier.

## 3. How to run it

```sh
python3 run.py --drill w08_routing
python3 run.py --drill w08_routing --failures 10
python3 run.py --drill w08_routing --task solutions/w08_reference.py
```

Look at the note line on the scorecard. It reports money spent, and the cost line
reports whether that is inside the cap.

## 4. Background: the idea from first principles

**The arithmetic.** Forty questions at the strong tier costs $0.060. The cap is
$0.030. So the expensive-everywhere approach cannot pass, no matter how accurate it
is.

Forty questions at the cheap tier costs $0.008, well inside the cap, and gets the 15
hard questions wrong. Accuracy: 62.5%.

Routing is the only path: cheap for easy, strong for hard. Fifteen strong calls plus
twenty-five cheap calls costs $0.0275.

**Why the baseline fails despite being correct.** The starting code is 100%
accurate. It fails because accuracy alone is not a result. A system that is correct
and four times over budget is a prototype, not a production system.

This is worth sitting with, because the instinct to optimise accuracy first is
strong and often wrong. The right target is the cheapest system that clears the
quality bar.

**What a routing signal can be.** Three options, in order of what to try first.

1. **Shape of the request.** A lookup names an identifier and asks for one
   attribute: "what is the status of order 8712". Reasoning asks why, or how, or to
   compare, or to design. A keyword classifier is free, fast, and gets most of the
   way.
2. **Stakes of being wrong.** A wrong shipping status is a support ticket. A wrong
   refund decision is money. Escalate by consequence, not only by difficulty.
3. **Measured confidence.** Let the cheap model report a confidence, and escalate
   when it is low. This is more accurate than keywords and more expensive than
   keywords. Build it only after keywords stop paying.

**The specific mistake in this dataset.** Do not route on question length. Length
correlates with difficulty in your imagination, not here. Check your assumption
against the data before building on it.

**The general form.** This is a cascade: a cheap filter followed by an expensive
fallback. Every production AI system runs one, whether or not anybody designed it.
The only question is whether the routing decision was deliberate.

## 5. The task, step by step

1. Run the starting code. It will be 100% accurate and fail on cost.
2. Read ten questions from each difficulty and write down what distinguishes them.
3. Write a classifier that maps the question text to a tier.
4. Put `tier: cheap` or `tier: strong` in the prompt accordingly.
5. Return the tier you used, so you can audit your routing.
6. Run it. Check both accuracy and the money spent.
7. If you are under budget and under 92%, find one more category of hard question.
   If you are over budget, find a category you are escalating unnecessarily.

## 6. How you are scored

`correct` is the fraction of questions where your answer contains the expected
answer string.

The drill passes when accuracy is at least 92% and total cost is at or below $0.030.
Both conditions must hold.

The note reports money spent, so you can see how much headroom you have.

## 7. Done when

- [ ] `python3 run.py --drill w08_routing` reports TARGET MET
- [ ] the cost note is under $0.030
- [ ] you can state your routing signal in one sentence
- [ ] you checked what the cheap tier got wrong rather than assuming
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

Accuracy without a cost line is a demo. Route by the cheapest signal that works, in
this order:

1. shape of the request
2. stakes of being wrong
3. measured confidence

And check your assumptions about what predicts difficulty before you build on them.
