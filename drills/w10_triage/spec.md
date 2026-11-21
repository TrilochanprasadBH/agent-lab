# Drill 10 — trace triage

**Target:** 90% correct root cause across 60 traces.

```
python3 run.py --drill w10_triage
```

You edit `task.py`. Return one of six labels.

## The six things that actually go wrong

| label | what it looks like |
|---|---|
| `loop` | the same call repeated until the budget dies |
| `context_overflow` | the prompt was longer than the window |
| `bad_tool_arg` | validation rejected the call before it ran |
| `auth` | 401 or 403 from a downstream service |
| `timeout` | the deadline passed while waiting |
| `wrong_tool` | a valid call that answered the wrong question |

## Why a grep fails

Every trace contains the word `error`. Most contain a keyword belonging to a
*different* cause, because real logs are full of sentences like "no timeout was
observed" and "authorization succeeded".

The baseline checks `"timeout"` first and scores **18%**. It is not looking at the
failure; it is looking at the surroundings.

## The move

**Read the right line.** The last line beginning with `error:` is the failure.
Everything above it is the path that led there.

Then **order by specificity**:

- `no progress after 6 steps` is a loop, even though the trace mentions retries;
- `does not satisfy the request` is a wrong tool, even though the tool is named
  `refund_order`;
- `missing_param` is a bad argument, even though auth also appears in the trace.

A rule set is a decision list, and a decision list is only as good as its order.

## Done looks like

- [ ] TARGET MET
- [ ] your first rule is the most specific one, and you can defend the order
- [ ] you fall back to the whole trace only when the primary line matches nothing
- [ ] you did not special-case a single trace to make the number move

## Why this is the most transferable drill here

Triage is what you do when an eval regresses and nobody knows why. The same three
habits — read the primary error, order your rules by specificity, resist adding a
keyword for every case — apply to eval rubrics, guardrails, and router thresholds.
