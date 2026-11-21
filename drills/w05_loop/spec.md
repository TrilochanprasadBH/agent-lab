# Drill 05 — the agent loop

**Target:** 90% correct, every case inside its step budget.

```
python3 run.py --drill w05_loop
```

Implement `solve(case, model)` returning `{"kind", "text", "steps"}`. Ten cases.

## The one sentence that matters

The model has no memory. Anything it knows, your loop put there.

The baseline calls the model once and returns whatever came back. It scores 20%,
not because the model is bad, but because a single call cannot see a tool result it
never received.

## The four decisions

**What the model sees.** Its prior calls *and their results*. A model without the
observation re-asks the same question, and every re-ask costs money.

**When to stop successfully.** A `final` payload, parsed and validated. Do not
pattern-match on prose.

**When to stop unsuccessfully.** Two conditions, and the second is the one people
skip:

- a step budget, and
- **repeated identical calls**. A model that loops on one call will do it forever.

**What to do with an error.** Feed it back. An error is an observation, and the
model can often correct itself once it sees `missing_param order_id`. Swallow it
and you get a confident wrong answer instead.

## Two cases that reward restraint

`a07` and `a08` are unfixable — the model repeats itself, or the tool always
errors. The correct outcome is `gave_up`, and it is scored as *correct*.

An agent that knows it is stuck is worth more than one that invents an answer.
This is the single most under-built part of production agents.

## Done looks like

- [ ] TARGET MET
- [ ] `a07` and `a08` report `gave_up` in ≤ 5 steps
- [ ] `a04` and `a05` recover *because* the error text reached the next prompt
- [ ] total calls are near 2.3 per case, not 5

## The failure you are learning to avoid

Traces where the same tool call appears forty times are common in the wild, and
they are never a model bug. They are a loop with no repeat detection and no budget.
