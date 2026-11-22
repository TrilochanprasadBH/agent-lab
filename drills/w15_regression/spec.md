# Drill 15 — Catching a release that breaks one thing

| | |
| --- | --- |
| **Goal** | Decide whether a change may ship, using per-category results and not only the average. |
| **Outcome** | A gate that gets all 30 decisions right, including the 12 where the average improves and one category gets worse. |
| **Target** | 90% correct decisions, zero false ships. |
| **Time** | 45 to 60 minutes. |

---

## 1. Why this drill exists

This is the most common way a production AI system degrades: not a crash, but a
sequence of releases that each improved the number somebody was watching.

The average goes up. One category goes down. Nobody looks at the category until a
customer does.

## 2. What you are given

- `data.py`: 30 pull requests.
- Each request contains per-item before and after results, grouped into three
  categories: refunds, international, long-context.
- The rule, which is the specification for this drill:

```
ship   if the overall result improves by at least 2 points
       and no category regresses by 2 points or more
block  otherwise
```

- The dataset contains:

| kind | count | property |
| --- | --- | --- |
| genuinely good | 12 | one category improves, others flat |
| one category regresses | 12 | average improves, one category drops 8 to 16 points |
| no real change | 6 | all categories flat within noise |

- `task.py`: the file you edit. It compares the overall averages only.

## 3. How to run it

```sh
python3 run.py --drill w15_regression
python3 run.py --drill w15_regression --failures 10
python3 run.py --drill w15_regression --task solutions/w15_reference.py
```

## 4. Background: the idea from first principles

**What the aggregate is.** One number across all items: the fraction that passed,
after the change minus before it.

**Why the aggregate can rise while a category falls.** Suppose a change affects 48
refund items and 24 international items.

- refunds improve from 65% to 90%, a gain of 25 points on 48 items;
- international drops from 70% to 58%, a loss of 12 points on 24 items.

Overall, the gain is larger than the loss, so the average rises by about 13 points.
The release looks like an improvement.

For an international customer, behaviour got 12 points worse. The average does not
represent them, because the average is not a person.

This is a mixture effect. When the composition of what improved and what regressed
differs, an average can move in the opposite direction to parts of the population.
The version you will meet most often is the dangerous one: average up, one group
down.

**Why a gate needs two thresholds.** The aggregate threshold answers "is this worth
the deployment". The category threshold answers "did we break anything". They are
different questions and both need an answer.

**What "no category regresses" should mean in practice.** Two points here, but in a
real system the number should be set per category, by consequence:

- a two-point drop in a category with 40% of traffic is an incident;
- a two-point drop in a category with 0.1% of traffic may be acceptable.

A single threshold for every category is a simplification. It is a reasonable
starting point, and it should be a deliberate decision rather than a default.

**Why the errors are not symmetric.** A false ship reaches users and may take days to
notice. A false block costs an engineer an hour. The thresholds should encode that
asymmetry: it is better to block a good change than to ship a bad one.

Put the asymmetry in the code, and put the reasoning in a comment. Otherwise the
next person will "fix" the conservative threshold without knowing why it was
conservative.

## 5. The task, step by step

1. Run the starting code. Count the false ships. It ships every pull request whose
   average rose, including the twelve that broke a category.
2. Compute the overall pass rate before and after.
3. Compute the pass rate before and after, separately, for each of the three
   categories.
4. Compute the aggregate delta and the delta for each category.
5. Ship only if the aggregate delta is at least 0.02 and every category delta is at
   least -0.02.
6. Return the reasoning with the decision, so a blocked change can be explained.

## 6. How you are scored

`correct decisions` is the fraction of the 30 pull requests where your decision
matches the truth. The drill passes at 90%.

The notes report false ships and false blocks separately. A false ship is the error
that matters; if you have any, fix those first even if the total score is acceptable.

## 7. Done when

- [ ] `python3 run.py --drill w15_regression` reports TARGET MET
- [ ] false ships is 0
- [ ] your thresholds are named constants, not inline numbers
- [ ] you check every category, not the ones you remember
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

Two rules for any release gate:

1. **Never gate on a single number.** Gate on the aggregate and on the worst
   category. The worst category is where the incident comes from.
2. **Make the asymmetry explicit.** A false ship reaches users; a false block costs
   an hour. Encode that in the thresholds and explain it in a comment.

The question to take to your own work: what is the worst category in your current
eval, and how would you know if it moved?
