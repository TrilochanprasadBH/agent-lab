# Drill 01 — schema repair & verification

**Target:** 90% field accuracy, under **$0.012** total cost, zero crashes.

```
python3 run.py
```

You edit `task.py`. Nothing else.

---

## The setup

You are given 48 invoices and a model that is roughly right and reliably messy.
On any given call it may:

| behaviour | how it shows up |
|---|---|
| prose wrapper | `Sure! Here's the data…` plus a fenced block |
| truncated JSON | the object stops mid-field, no closing brace |
| trailing comma | `"total": 4116.55,}` |
| numbers as strings | `"total": "4,116.55"` |
| wrong party | returns the *customer* as the vendor |
| subtotal as total | arithmetic no longer adds up |
| refusal | a polite sentence instead of data |

Every one of these is something you can detect. None of them is fixed by
phrasing the prompt better, which is the point.

## The rules

1. Call the model at least once per document. A pure regex over the invoice
   solves the corpus and teaches you nothing, so the harness rejects it.
2. No network, no API keys. The model is local and deterministic.
3. You may read `agentlab/` to understand the scoring. You may not edit it —
   if you change the grader, you are measuring your grader.

## What you are actually practising

The four moves from this drill generalise to every extraction, classification,
or tool-calling system you will ever build:

1. **Repair before parse.** Model output is text, not JSON. Treat it as text.
2. **Normalize at the boundary.** One place converts money, dates, currencies.
   Downstream code should never see `"1.350,00 EUR"`.
3. **Validate with arithmetic and with the source.** `subtotal + tax == total`
   is a free integrity check. So is "does this vendor actually appear on the
   supplier line?"
4. **Retry selectively.** Retry because you detected a specific defect, not
   because you feel nervous. And after N attempts, return your best partial
   record rather than nothing.

## Hint ladder

Try to finish before opening these.

<details><summary>Hint 1 — where the points are lost</summary>

Run with `--failures 10`. Roughly half the missing fields come from a handful of
documents whose JSON never parsed at all. Fixing parsing alone is worth about
fifteen points.
</details>

<details><summary>Hint 2 — repairing truncated JSON</summary>

A truncated object is one with unbalanced braces and possibly an unterminated
string. You can walk the fragment, track whether you are inside a string and how
many braces are open, then append the closers. If the tail ends mid-value, cut
back to the last comma first.
</details>

<details><summary>Hint 3 — catching the wrong vendor</summary>

The corrupted vendor is always the party *being billed*. Compare the predicted
vendor against the document's bill-to line and its supplier line. If it matches
the bill-to and not the supplier, you have a defect — and a very cheap one to
detect.
</details>

<details><summary>Hint 4 — the free arithmetic check</summary>

`subtotal + tax` must equal `total`. When the model returns the subtotal as the
total, this fails immediately. Note the blind spot: on a 0% tax invoice the two
are equal and this check cannot help you. Every heuristic has one.
</details>

## Done looks like

- [ ] `python3 run.py` reports TARGET MET
- [ ] cost is under budget without blanket retries
- [ ] `python3 run.py --seed 11` also passes — you did not tune to one seed
- [ ] you can explain, in two sentences, which defect each of your checks catches

Once it passes, write it up in `progress.md`. The retro is the part that makes
the skill stick; the score is just evidence.
