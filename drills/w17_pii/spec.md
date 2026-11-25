# w17 — Redacting personal data

| | |
| --- | --- |
| **Goal** | Find every piece of personal data in a support message, and nothing else. |
| **Outcome** | A redactor with 97.7% span recall and 98% precision on forty messages. |
| **Target** | recall ≥ 93%, precision ≥ 90%, under $0.10 of model calls |
| **Time** | 60 to 90 minutes |

## 1. Why this drill exists

Before a message goes to a model, the personal data in it has to go. That is a legal
requirement in most places and a practical one everywhere: a support transcript with a card
number in it becomes a card number in a vendor's logs.

The two errors are not symmetric.

| error | what happens | cost |
| --- | --- | --- |
| leak | the name, card or address reaches the model | the failure the step exists to prevent |
| over-redaction | an order number becomes `[REDACTED]` | the agent can no longer act on the message |

A redactor tuned for one is bad at the other. The drill scores recall, because a leak is the
failure, and puts a hard floor under precision, because a message you cannot act on is not a
protected message — it is a deleted one.

## 2. What you are given

- `data.py`: forty support messages, 88 labelled spans across seven categories: email, phone,
  card, IBAN, national identifier, address, name.
- `data.NameModel`: a tagger that finds names and addresses, misses about one in seven of each,
  and has a one-in-four chance of calling a company name a person.
- `data.Luhn`: the checksum that separates a card number from a sixteen-digit order number.
- `data.DISTRACTORS`: numbers that look personal and are not. Every message carries one.
- `task.py`: emails and sixteen-digit runs. Precise on emails, blind to five categories, and it
  redacts order numbers.
- `check_labels.py`: verifies the labels, including that every occurrence of a value is labelled.

The corpus is authored, and the labels are the artefact. That is allowed here for one reason:
a corpus of real personal data cannot be committed, and no public sample contains the exact
ambiguities this drill turns on — an order number shaped like a card, a surname that is also a
word, a name with a lowercase particle in the middle.

## 3. How to run it

```sh
python3 drills/w17_pii/check_labels.py
python3 run.py --drill w17_pii
python3 run.py --drill w17_pii --task solutions/w17_reference.py
python3 -m unittest tests.test_drills -v
```

## 4. Background: four layers, in order of trust

**Checksums beat shapes, and shapes beat guesses.** A sixteen-digit number is a card only if it
passes Luhn:

```
4111 1111 1111 1111   Luhn ok    -> card
4000056655665557      Luhn fails -> order number
```

The baseline fails exactly here. It counts digits, so it redacts both, and its precision drops
to 80% on a corpus where the only ambiguity is a number.

**Structured identifiers are a pattern problem.** Email, phone, IBAN and national identifier
have shapes narrow enough that a regex is precise. The rule is to validate after matching: an
IBAN by length, a phone by counting digits once punctuation is stripped.

**Names need context, and a list is not enough.** A gazetteer catches the common ones and
misses the rest, which is why a name tagger exists. Neither is sufficient: the tagger misses one
name in seven, and the gazetteer does not contain everyone.

**Merge, do not concatenate.** When two detectors return overlapping spans, the longer one wins
only if it is the safer category. A model span that says "48 Bartlett Street, Somerville MA
02145" should replace a gazetteer span that says "Bartlett Street". A model span must never
replace an email or a card number it happens to overlap.

## 5. The task, step by step

1. Run the baseline. Read the leak note: it lists what you are missing, by category.
2. Add the structured patterns. Validate the card with `data.Luhn`.
3. Call the tagger once per message, with the message id in the prompt. Parse its JSON.
4. Merge: drop invalid spans, drop overlaps, and let a longer name or address span replace a
   shorter one. Never let the model touch a structured category.
5. Add the context and gazetteer rules for names the tagger missed.
6. Run it, read the leaks, and decide what you are willing to leave.

Return `{"spans": [(start, end, category), ...]}` with offsets into the original text.

## 6. How you are scored

| metric | weight |
| --- | --- |
| recall | the accuracy line, target 93% |
| precision | hard floor: below 90%, the run scores zero |
| malformed spans | hard floor: any span outside the text or with an unknown category scores zero |
| cost | cap $0.10 of model calls |
| crashes | must be zero |

A gold span counts as recalled when **every character** of it is covered, by one prediction or
by several. Two names redacted separately is a success, not a leak.

## 7. Done when

- [ ] `python3 run.py --drill w17_pii --task solutions/w17_reference.py` reports TARGET MET
- [ ] `python3 drills/w17_pii/check_labels.py` reports zero problems
- [ ] the baseline scores zero, and you can say which two rules make it fail
- [ ] you can name the categories you still leak and why
- [ ] the reference's two residual leaks are explained: a name whose lowercase particle no rule
      covers, and an address where the postcode ends before the city

## 8. Carry forward

The reference reaches 97.7% and 98%, and both numbers are about this corpus. Forty authored
messages contain every shape the patterns were written for; a real inbox contains addresses
without postcodes, names in scripts the gazetteer has never seen, and numbers that pass Luhn by
coincidence. **Treat the residual leaks as the honest number and the 100% you could reach by
widening a regex as a precision loss waiting to happen.**

What this drill does not model: reversible tokenisation (you redact, you do not restore), a
vault with access control, or the retention policy. Those are the other half of a PII pipeline,
and none of them can be measured with a span metric.
