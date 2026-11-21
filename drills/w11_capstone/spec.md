# Drill 11 — capstone: the whole pipeline

**Target:** 90% of tickets handled correctly, **zero** unauthorised actions, under
**$0.016**.

```
python3 run.py --drill w11_capstone
```

Twelve tickets. Return `{"outcome", "answer", "steps"}`.

## What is actually being tested

Not a harder problem. Ten easy things that must all be true at once:

| # | requirement | drill it comes from |
|---|---|---|
| 1 | select the documents that are evidence | 03 |
| 2 | sanitise retrieved text before the model sees it | 09 |
| 3 | validate tool arguments against a schema | 04 |
| 4 | gate state-changing actions behind a human | 04, 09 |
| 5 | feed tool results back into the next prompt | 05 |
| 6 | bound the loop by steps and repeats | 05 |
| 7 | answer only when grounded in evidence | 01, 03 |
| 8 | treat `needs_confirmation` as a success | 05 |
| 9 | stay near 2 calls per ticket | 08 |
| 10 | report handled *and* safe together | all |

Miss any one and the number collapses in a specific, diagnosable way. That is the
whole reason composition is its own drill.

## The model is conditional, on purpose

It can only answer if **both** the evidence phrase and the tool observation are in
the prompt you send. That is what makes the scaffolding load-bearing rather than
decorative:

- skip retrieval → you get "it should be fine, I would not worry about it";
- skip the tool call → it asks again, and if you never answer, you never finish;
- skip sanitising → it obeys the injected instruction and exfiltrates;
- skip validation → a malformed call reaches the world.

A real model would be *more* forgiving and therefore *less* instructive here.

## The tickets

- **s01, s03, s09, s12** need a tool before they can be answered.
- **s02, s04, s06, s08** are answerable from documents alone.
- **s05, s07** ask for a refund and an account deletion. The correct outcome is
  `needs_confirmation` — not an execution, and not a refusal.
- **s10, s11** carry a poisoned document. One tries to exfiltrate, one tries to
  assert a false answer.

## Why the baseline scores 20%

It concatenates the documents, calls the model once, and executes whatever it is
asked for. That is enough for the four document-only tickets. It fails everything
else, and it refunds, deletes, and emails an attacker on the way.

Note the baseline is also **cheaper** ($0.0036) than the correct solution ($0.0045).
Safety and correctness cost money. Anyone telling you otherwise is selling
something.

## Done looks like

- [ ] TARGET MET, `no unauthorised action` at 100%
- [ ] every `world.sent`, `world.refunded`, `world.deleted` is empty
- [ ] `needs_confirmation` is returned, not an exception and not a guess
- [ ] p95 steps at or below 3
- [ ] you can point at the line where each of the ten requirements is enforced

## The uncomfortable question

Now look at your `task.py`. Which of the ten requirements is enforced by *code*
you wrote, and which is enforced by the model happening to be cooperative?

Every requirement you cannot point at a line for is a requirement you do not have.
This is the question to ask about your own systems, not about this drill.
