# Drill 08 — routing and cost

**Target:** 92% correct, under **$0.030** total.

```
python3 run.py --drill w08_routing
```

You edit `task.py`. Write `"tier: cheap"` or `"tier: strong"` into the prompt.

## Two models

| tier | cost | behaviour |
|---|---|---|
| cheap | $0.0002 | right on lookups, wrong on reasoning |
| strong | $0.0015 | right on everything |

Seven and a half times the price. Forty questions.

- Always strong: **100% accurate, $0.060** — fails the cap by a factor of two.
- Always cheap: **62% accurate, $0.008** — comfortably affable, and wrong.
- Routed: **100% at $0.0275** — inside the budget with room.

The interesting thing is that the baseline is *correct*. It is just unaffordable.
Accuracy without a cost line is not a result; it is a demo.

## How to route, in the order you should try it

1. **By shape of the request.** "What is the status of X" is a lookup. "Why did X
   fail", "compare A and B", "design a retry policy" are reasoning. A keyword
   classifier gets most of the way, and it costs nothing.
2. **By consequence of being wrong.** A wrong shipping status is a support ticket.
   A wrong refund decision is money. Escalate by stakes, not just difficulty.
3. **By measured confidence.** Let the cheap model report confidence, escalate
   below a threshold. More accurate than keywords, more expensive than keywords,
   and worth building only once keywords have stopped paying.

## The mistake to avoid

Do not route on how *long* the question is. Length correlates with difficulty in
your imagination and not in this dataset.

## Done looks like

- [ ] TARGET MET, and the cost note is under $0.030
- [ ] you can name your routing signal in one sentence
- [ ] you checked what the cheap tier got wrong, rather than assuming

## Why this matters

Every production agent runs a cost cascade whether or not anyone designed one. The
only question is whether the routing decision was deliberate. Undesigned routers
default to "always the biggest model", which is why so many agent budgets collapse
in the second month.
