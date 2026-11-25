# w18 — Always-valid JSON

| | |
| --- | --- |
| **Goal** | Turn an invoice message into an object that satisfies a schema, without losing the content the schema carries. |
| **Outcome** | 100% valid objects at 86.7% correct, in one call per case. |
| **Target** | validity ≥ 99%, correctness ≥ 82%, under $0.020 |
| **Time** | 45 to 60 minutes |

## 1. Why this drill exists

"Always-valid JSON" is the requirement everyone writes in the ticket, and it is only half a
requirement. The free-form model in this drill breaks its output in two ways:

**Visible.** Truncated, a trailing comma, a sentence in front of the object, `"1,234.50"` where
the schema says a number, `12 March 2026` where it says `YYYY-MM-DD`, a missing key. Every one
is detectable, and every one can be fixed by a parser, a repair function, or another sample.

**Invisible.** The message names a seller and a buyer. Sometimes the model returns the buyer.
The JSON is perfect. The total and the date are right, the vendor is the customer, and nothing
in the text says so.

The drill's number is *valid and correct*, and the table shows why: as validity rises, the share
of errors that are invisible rises with it. A system judged on validity alone gets worse at the
thing that matters while its dashboard turns green.

## 2. What you are given

- `data.py`: 30 invoice messages with a seller, a buyer, a date and a total.
- `data.ExtractionModel.complete(prompt, schema=None)`: free text by default; pass the schema and
  the sampler emits a valid object, at twice the price.
- `data.SCHEMA`: three fields, with a date format and a numeric type.
- `task.py`: `json.loads` and an empty dict on failure.
- `sweep.py`: the four strategies compared, and the source of every number here.

## 3. How to run it

```sh
python3 drills/w18_constrained_json/sweep.py
python3 run.py --drill w18_constrained_json
python3 run.py --drill w18_constrained_json --task solutions/w18_reference.py
```

## 4. Background: four strategies, and what each one actually buys

| strategy | valid | correct | invisible | calls | cost |
| --- | --- | --- | --- | --- | --- |
| parse only | 36.7% | 33.3% | 3.3% | 1.00 | $0.0060 |
| repair | 56.7% | 50.0% | 6.7% | 1.00 | $0.0060 |
| retry ×3 | 63.3% | 53.3% | 10.0% | 2.07 | $0.0124 |
| schema | **100%** | **86.7%** | 13.3% | 1.00 | $0.0120 |

**Repair is worth about twenty points of validity and costs nothing.** Strip the prose, close the
object, drop the trailing comma. It does not touch truncation, a missing key, or a type error,
which is why it stops at 56.7%.

**Retries converge slowly.** With 36.7% of replies valid per attempt, reaching 99% needs about
eleven attempts, and eleven attempts cost $0.066 — more than three times the cap. Retrying is the
right answer when the failure rate is low and the wrong answer when it is 63%.

**The schema is a guarantee about shape, bought at 2× the price.** It makes the visible defects
impossible, because the sampler cannot emit them. It does not touch the invisible one: 13.3% of
the objects are perfectly valid and name the buyer.

**The invisible column is the one to read.** It rises from 3.3% to 13.3% across the table, and
that is not the model getting worse. It is the denominator: when every reply is valid, every
error becomes invisible. **Improving validity converts loud failures into quiet ones.**

## 5. The task, step by step

1. Run the baseline and `sweep.py`. Note the gap between `valid` and `correct` in every row.
2. Pass the schema to `complete`. Parse the reply, and validate it anyway — a guarantee you do
   not check is a guarantee you do not have.
3. Run the reference. It reaches 100% valid and 86.7% correct.
4. Read the four "valid but wrong" failures. Compare the vendor to the message's seller and buyer.
5. Decide what you would add. The brief's last section is about that, and the drill does not
   build it.

Return a dict with `vendor`, `invoice_date` and `total`.

## 6. How you are scored

| metric | weight |
| --- | --- |
| valid and correct | the accuracy line, target 82% |
| validity | hard gate: below 99%, the run scores zero |
| cost | cap $0.020 of model calls |
| crashes | must be zero |

The gate is the pedagogical point: a run that is 80% correct on objects that are 60% valid is
not a 80% system, it is a system that will crash a downstream service four times in ten.

## 7. Done when

- [ ] `python3 run.py --drill w18_constrained_json --task solutions/w18_reference.py` reports TARGET MET
- [ ] you can explain why repair stops at 56.7% and retries at 63.3%
- [ ] you can state the number of retries needed for 99% validity, and its cost
- [ ] you can name the four cases the reference gets wrong and why no schema catches them
- [ ] you can say what validity does to the *visibility* of errors, not just their count

## 8. Carry forward

The schema fixes format. The remaining 13.3% is an extraction error, and the only fix is a check
against a source that is not the model: does the returned vendor appear where the message names
the seller, and not where it names the buyer? That is `w01`'s cross-check lesson at a different
layer, and it is the next thing to build, not this drill's job.

What this drill does not model: a real grammar-constrained sampler, where the guarantee comes
from the token-level mask rather than from an API flag. The property is the same — invalid
outputs become unreachable — and the cost is the same in kind, more work per token. What it also
does not model is a schema change, which in production is the failure that takes the service
down: the fields are right, the names moved.
