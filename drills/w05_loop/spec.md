# Drill 05 — Running a task that takes several steps

| | |
| --- | --- |
| **Goal** | Write an agent loop that reaches a correct answer, or stops deliberately. |
| **Outcome** | A `solve` function that handles 9 of 10 multi-step tasks correctly and never exceeds its step budget. |
| **Target** | 90% correct, every case inside its budget. |
| **Time** | 60 to 90 minutes. |

---

## 1. Why this drill exists

A single model call cannot do work that requires a lookup, then a decision based on
the lookup, then another lookup. That needs a loop.

A loop is easy to write and easy to get wrong. The two classic failures are an agent
that stops too early because it never saw a tool result, and an agent that never
stops because nothing tells it to.

This drill gives you ten tasks where both failures are possible.

## 2. What you are given

- `data.py`: a small world with customers and orders, and ten cases.
- Each case contains the user's request and a script: the sequence of things the
  model would say if something kept calling it.
- The model has no memory. It only knows what is in the prompt you send.
- `task.py`: the file you edit. It calls the model once and returns what came back.

Case expectations:

| case | situation | correct outcome |
| --- | --- | --- |
| a01, a02, a03 | two or three steps needed | `answer` with the right text |
| a04 | first tool call is malformed | `answer` after recovery |
| a05 | model invented a tool name | `answer` after recovery |
| a06 | look-up of something that does not exist | `answer` explaining it |
| a09 | two lookups needed | `answer` with both |
| a10 | model answers immediately | `answer` |
| a07 | model repeats the same call forever | `gave_up` |
| a08 | model asks for a tool that always errors | `gave_up` |

## 3. How to run it

```sh
python3 run.py --drill w05_loop
python3 run.py --drill w05_loop --failures 10
python3 run.py --drill w05_loop --task solutions/w05_reference.py
```

## 4. Background: the idea from first principles

**What an agent loop is.** A loop with four jobs:

1. Build the prompt, including everything that has happened so far.
2. Call the model.
3. If the model asked for a tool, run it and record the result.
4. Decide whether to continue or stop.

**Job 1 is the one people underestimate.** The model is stateless. It does not
remember the previous call. If you send only the original question, the model has no
way to know that a lookup already happened. It will ask again.

So the prompt must contain the history: which tools were called, with what
arguments, and what came back. The model's behaviour is entirely determined by what
you put in that prompt.

**Job 4 needs two different stopping conditions.**

*Successful stop.* The model produced a final answer. You parse it, validate it, and
return it.

*Unsuccessful stop.* This is the part that gets skipped, and it is why agents run
forever in production. There are two cases to detect:

- **Step budget.** If you have looped N times, stop. Every loop iteration costs
  money, and a confused model will keep going as long as you let it.
- **Repeated identical calls.** If the model asks for the same tool with the same
  arguments it already asked for, it is stuck. It will keep doing this indefinitely.
  Detect it and stop.

Stopping is a correct outcome. `gave_up` is scored as success in cases a07 and a08,
because an agent that knows it is stuck is more valuable than one that invents an
answer.

**What to do with tool errors.** Errors are observations. If the tool says
`missing_param order_id`, put that in the next prompt. The model can often correct
itself, and case a04 exists to check that you let it.

If you swallow the error and continue with no information, the model will produce a
confident answer with no relationship to reality.

## 5. The task, step by step

1. Run the starting code. Every case fails except the one-step ones.
2. Write a parser that extracts either a tool call or a final answer.
3. Maintain a list of observations. Put them in every prompt.
4. Call the tool through a validated registry. Do not call handlers directly.
5. On success, append the result. On failure, append the error message.
6. Track a set of previously seen call signatures. If a signature repeats, return
   `gave_up`.
7. Stop at the step budget and return `gave_up`.
8. Return the number of model calls in `steps`.

## 6. How you are scored

For each case, your result is correct if all three conditions hold:

1. `kind` matches the expected kind (`answer` or `gave_up`).
2. `text` contains the expected substring, when one is given.
3. `steps` is within the case's budget.

`accuracy` is the fraction of cases that meet all three. The drill passes at 90%,
which means nine of ten.

The note reports how many cases stayed inside their step budget. A run at 100%
accuracy with cases over budget would still indicate a broken loop, so check the
note as well as the score.

## 7. Done when

- [ ] `python3 run.py --drill w05_loop` reports TARGET MET
- [ ] a07 and a08 return `gave_up` within five steps
- [ ] a04 and a05 recover because the error text reached the next prompt
- [ ] total model calls average near 2.3 per case, not 5
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

A loop is four decisions: what the model sees, when to stop successfully, when to
stop unsuccessfully, and what to do with an error.

The second and third are the ones that separate a demo from a system. Detect
repeated calls, enforce a step budget, and treat giving up as a valid result.
