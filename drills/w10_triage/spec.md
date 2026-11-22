# Drill 10 — Naming the cause of a failure

| | |
| --- | --- |
| **Goal** | Read an agent trace and identify which of six failure modes caused it. |
| **Outcome** | A classifier that assigns the correct root cause to 90% of 60 traces full of misleading log lines. |
| **Target** | 90% correct causes. |
| **Time** | 45 to 60 minutes. |

---

## 1. Why this drill exists

When an eval regresses, someone has to read the failures and decide what class of
problem they are. That decision determines what gets fixed.

Doing it by grep is fast and wrong. Real logs contain the words for every failure
mode, because they describe what did not happen as well as what did.

This drill is classification, with deliberately noisy inputs.

## 2. What you are given

- `data.py`: 60 traces, 10 for each of six causes.

| label | meaning |
| --- | --- |
| `loop` | the same call repeated until the budget ran out |
| `context_overflow` | the prompt was longer than the window |
| `bad_tool_arg` | validation rejected the call |
| `auth` | 401 or 403 from a downstream service |
| `timeout` | the deadline passed |
| `wrong_tool` | a valid call that answered the wrong question |

- Each trace contains several `step` lines, a distractor line, and one primary
  `error:` line.
- The distractor mentions a different failure mode. Many traces contain the word
  "timeout" without being a timeout, in a sentence like "no timeout was observed".
- `task.py`: the file you edit. It greps for the first keyword it recognises.

## 3. How to run it

```sh
python3 run.py --drill w10_triage
python3 run.py --drill w10_triage --failures 10
python3 run.py --drill w10_triage --task solutions/w10_reference.py
```

## 4. Background: the idea from first principles

**What classification is.** You have inputs and a fixed set of labels. You want a
rule that maps each input to the right label. Here the inputs are traces and the
labels are the six causes above.

**Why keyword search fails.** A grep answers "does this word appear anywhere". The
question you actually have is "what went wrong". Those are different questions.

In these traces, every one contains the word "error", and most contain a word
belonging to a different cause. So the first keyword you test will match the wrong
traces. The baseline tests "timeout" first and scores 18%.

**The primary error line.** Each trace ends with a line beginning `error:`. That
line is the failure. The lines above it are the path that led there, and the
distractor line is a statement about something that did *not* happen.

So the first rule is: extract the last line starting with `error:` and classify that
line, not the whole document. This single change accounts for most of the gap
between the baseline and a good solution.

**Why a decision list needs an order.** Once you have several patterns, they can all
match the same input. The order in which you test them decides the answer.

Order by specificity: the most particular evidence first.

- `no progress after 6 steps` is a loop, even though the trace mentions retries.
- `does not satisfy the request` is a wrong tool, even though the tool is named
  `refund_order`.
- `missing_param` is a bad argument, even though the trace also mentions
  authorisation.

If a general rule runs first, it swallows the cases the specific rule was written
for. This is the most common bug in rule-based systems of every kind, including eval
rubrics and guardrails.

**The fallback.** If nothing matches the primary line, you may fall back to scanning
the whole trace. Do that only after the specific rules have failed, and prefer the
same ordering.

## 5. The task, step by step

1. Run the starting code. Read a few traces by hand to see the pattern.
2. Write a function that extracts the last line beginning with `error:`.
3. Write an ordered list of (label, pattern) pairs, most specific first.
4. Match the primary line against the list and return the first hit.
5. If nothing matches, fall back to the whole trace.
6. Read every remaining failure and check whether the cause is a missing pattern or
   a bad ordering.

## 6. How you are scored

`correct cause` is the fraction of the 60 traces where your label matches the true
cause. The drill passes at 90%.

The failure modes section reports confusions in the form `true -> predicted`, which
tells you which pair of labels you are mixing up.

## 7. Done when

- [ ] `python3 run.py --drill w10_triage` reports TARGET MET
- [ ] your first rule is the most specific one, and you can explain why
- [ ] the fallback runs only when the primary line matched nothing
- [ ] you did not special-case a single trace to move the number
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

Triage is a decision list, and a decision list is only as good as its order.

1. read the primary error, not the surroundings
2. order rules by specificity
3. fall back to the whole input only after specific rules fail

The same three habits apply to eval rubrics, router thresholds, and guardrails.
