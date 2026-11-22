# Drill 01 — Turning model output into data

| | |
| --- | --- |
| **Goal** | Convert unreliable text from a model into validated records. |
| **Outcome** | A function that extracts four invoice fields with 90% accuracy, under a cost cap, from a model that corrupts its own output. |
| **Target** | 90% accuracy, cost under $0.012, zero crashes. |
| **Time** | 60 to 90 minutes. |

---

## 1. Why this drill exists

A model returns a string. Your program needs a record: a vendor name, a date, a
currency, an amount.

Almost every reliability problem in an AI application lives in that gap. The model
is not the part you control. The conversion is.

This drill gives you a model that is roughly right and frequently malformed, and
asks you to build the layer that turns its output into something you can trust.

## 2. What you are given

- `data.py`: 48 invoices, generated deterministically, each with ground truth.
- `model.py`: a simulated model. It reads the invoice with regular expressions,
  then corrupts its own answer about half the time.
- `task.py`: the file you edit. It currently parses the response naively.

The failure types, and how often they occur:

| behaviour | example | probability |
| --- | --- | --- |
| clean JSON | `{"total": 4116.55}` | about half |
| prose then JSON | `Sure! Here's the data: {...}` | 12% |
| truncated object | `{"total": 4116` | 12% |
| numbers as strings | `"total": "4,116.55"` | 6% |
| wrong party | the customer's name instead of the vendor | 12% |
| subtotal returned as total | arithmetic no longer adds up | 10% |
| trailing comma | `{"total": 4116.55,}` | 10% |
| refusal | a polite sentence instead of data | 6% |

## 3. How to run it

From the repository root:

```sh
python3 run.py --drill w01_extraction
```

See what broke:

```sh
python3 run.py --drill w01_extraction --failures 10
```

Check you did not tune to one random seed:

```sh
python3 run.py --drill w01_extraction --seed 11
```

See a working version, after you have tried:

```sh
python3 run.py --drill w01_extraction --task solutions/w01_reference.py
```

## 4. Background: the idea from first principles

**A model call returns text.** Not a dict, not JSON, not a typed object. Whatever
structure you want has to be built on your side, and every step of that construction
can fail.

There are three distinct kinds of failure, and they need three different fixes.

**Failure 1: the response is not parseable as JSON.**

JSON is a strict format. A trailing comma, a missing brace, or a sentence in front
of the object makes the whole thing invalid. One of the most common causes is
truncation: the model stopped because it hit a length limit, leaving an unbalanced
object.

The fix is mechanical: strip text before the first `{`, ignore code fences, remove
trailing commas, and if the object is unterminated, close the open braces.

**Failure 2: the response parses but the values are the wrong type.**

`"total": "4,116.55"` is valid JSON. It is not a number. It also cannot be converted
with `float()` because of the thousands separator. Some locales write `1.350,00`
for the same amount.

The fix is normalisation: one function that turns any reasonable representation of
money into a float, and one that turns any date format into ISO 8601, and one that
turns a currency symbol into a code. Do this once, at the boundary, so the rest of
your program never sees the mess.

**Failure 3: the response parses, the types are right, and the value is wrong.**

The model returned `Stark Industrial` as the vendor. That is the customer. It
returned the subtotal as the total. It dropped a field.

No amount of parsing or normalisation fixes this, because nothing about the value
looks malformed. You need an independent check.

Two checks are available here for free:

- **Arithmetic.** `subtotal + tax` must equal `total`. If it does not, one of the
  three values is wrong.
- **The source document.** The vendor must appear on the supplier line of the
  invoice, not only on the customer line.

Both checks are cheap, and both catch failures the parser cannot see.

**Retrying.** When a check fails, you can ask the model again. A retry costs money
and is not guaranteed to help, so retry only when you have detected a specific
defect. Sending the same prompt twice asks the same question twice; changing the
prompt changes the answer. After a small number of attempts, return your best
partial record rather than nothing.

**Why not parse the invoice directly?** You could, and on this dataset it would
work, because the invoices are generated from a template. The harness rejects it:
you must call the model. In real work the reason is stronger. The documents you
receive are not generated from your template, there are thousands of formats, and
the day the format changes your parser silently breaks. The model absorbs format
variation; your code should absorb the model's unreliability.

## 5. The task, step by step

1. Run the starting code. Read the failure modes. Roughly half of the missing
   fields come from a handful of documents whose JSON never parsed.
2. Write `parse_json(text)` that handles fences, prose, trailing commas, and
   truncation.
3. Write normalisers for money, currency, and date. Use them on every field.
4. Add the arithmetic check. Retry when it fails.
5. Add the vendor check against the document. Retry when it fails.
6. Keep the best partial record. Do not return `{}` after three failures.
7. Run with `--seed 11` to confirm you did not tune to one sample.

## 6. How you are scored

Four fields are scored: `vendor`, `invoice_date`, `currency`, `total`.

| field | match rule |
| --- | --- |
| vendor | equal after lowercasing and removing punctuation and spaces |
| invoice_date | equal as a calendar date, after parsing any common format |
| currency | equal as a three-letter code |
| total | within 0.01 of the true amount |

`accuracy` is the mean of the four field accuracies, each computed over all 48
documents.

`cost` is the sum of the simulated token costs of every call you made. The cap is
$0.012. A solution that reaches 95% for $0.02 fails.

`crashes` must be zero. An exception counts as a crash and the item scores zero.

`model calls` must average at least 0.9 per document. This prevents solving the
drill by parsing the invoices directly.

The drill passes when accuracy is at least 90%, cost is within the cap, and there
are no crashes.

## 7. Done when

- [ ] `python3 run.py --drill w01_extraction` reports TARGET MET
- [ ] the run with `--seed 11` also reports TARGET MET
- [ ] you can name which specific check catches each corruption type
- [ ] your cost is comfortably under the cap without retrying everything
- [ ] you have written the entry in `progress.md`

## 8. Carry forward

When a model produces structured data, use four steps in this order:

1. repair the text
2. normalise the values
3. validate against arithmetic and against the source
4. retry only on a detected defect, and return the best partial result
