# w23 — Fine-tune, retrieve, or prompt

| | |
| --- | --- |
| **Goal** | Choose the cheapest architecture that clears the quality bar, for 24 scenarios with real volumes and real constraints. |
| **Outcome** | 100% of 24 decisions, from 12.5% for the industry default. |
| **Target** | 90% of decisions correct |
| **Time** | 60 to 90 minutes |

## 1. Why this drill exists

"Should we fine-tune or use RAG" is usually answered with a preference, and the preference is
usually "RAG". It is a decision with an arithmetic answer, and the arithmetic is short enough to
do on a napkin:

> Filter the options by what is possible. Filter again by what clears the quality bar. Among the
> survivors, take the cheapest per day.

Each of the three passes removes a different kind of mistake. Skipping the first one picks an
option you cannot build. Skipping the second picks the cheapest answer that fails your eval.
Skipping the third picks the best answer you do not need. The sweep measures all three mistakes,
and each one costs between 38 and 62 points.

The corpus is 24 product scenarios. Each one has a volume, a prompt and output size, a corpus,
a label set, how often the facts change, whether sources must be cited, and three quality numbers
measured on that product's eval set. **The quality numbers are inputs, not assumptions**, because
the entire point is that you measure them for your task instead of believing a blog post.

## 2. What you are given

- `data.SCENARIOS`: the 24 scenarios, with `summary`, `kind`, and the numbers.
- `data.APPROACHES` and `data.ANSWERS`: the options and the possible answers, including `none`.
- The cost constants: large model at $3.00/$15.00 per million tokens in and out, small model at
  $0.30/$1.20, training at $8.00 per million tokens over 3 epochs, retrieval at $0.0004 per
  request, and the amortisation window per `facts` value (365 days for `never`, 30 for `monthly`).
- `task.py`: always retrieve.
- `sweep.py`: six strategies, the per-kind breakdown, and the daily cost of every option.
- `check_labels.py`: recomputes every decision with a second implementation.

The scenarios are authored, because a decision drill needs exact numbers and a known constraint
set. The answers are not authored: they are the output of the cost model, and `check_labels.py`
proves that each stored answer is the unique cheapest option that clears the bar.

## 3. How to run it

```sh
python3 drills/w23_finetune/check_labels.py
python3 drills/w23_finetune/sweep.py
python3 run.py --drill w23_finetune
python3 run.py --drill w23_finetune --task solutions/w23_reference.py
```

## 4. Background: three passes, and the two crossovers

| strategy | overall | cost | constraint | none | what it misses |
| --- | --- | --- | --- | --- | --- |
| always rag | 12.5% | 0% | 38% | 0% | everything that is not a retrieval problem |
| always fine-tune | 41.7% | 80% | 25% | 0% | every low-volume, citation and changing-facts case |
| cheapest, no filter | 54.2% | 100% | 38% | 0% | the option it picked cannot be built |
| no quality bar | 62.5% | 100% | 62% | 0% | the cheapest option is below the bar |
| most accurate | 62.5% | 30% | 75% | 100% | the cost of the best answer |
| **the three passes** | **100%** | 100% | 100% | 100% | nothing |

The last four rows are the interesting ones. `cheapest, no filter` computes every cost correctly
and still loses 46 points, because the cheapest option in the table is regularly one you cannot
build: fine-tuning on no labels, on facts that change weekly, or on a citation requirement.
`no quality bar` keeps the feasibility pass and loses 38, because the small model is cheap and
below the bar. `most accurate` keeps both filters and loses 38 the other way — it buys quality
nobody asked for.

### Retrieval never wins on cost

Add the retrieved tokens to the prompt and a fee per request and retrieval is **strictly more
expensive per request** than prompting. It cannot win a cost comparison. It wins when prompting
misses the bar, and that is the only reason it appears in this corpus: all three retrieval
answers are scenarios where prompting is below the bar, and `check_labels.py` asserts it.

That reframes the usual debate. RAG is not a cost optimisation; it is a quality purchase with a
recurring bill. If prompting already clears your bar, retrieval is money for nothing.

### Fine-tuning is a fixed cost, so its answer depends on volume

The training cost is paid once and amortised over the window in which the facts stay still. The
saving per request is roughly nine tenths of the large model's bill. Break-even is therefore:

```
training per day / saving per request
```

Scenario `t02` is the worked example: 5,000 examples at 600 tokens, 3 epochs, $8 per million
training tokens.

```
training        5000 x 3 x 600 x 8 / 1e6                = $72.00
per day         72 / 365                                 = $0.197
saving/request  (900x3 + 250x15)/1e6 - (900x0.3 + 250x1.2)/1e6
                                                        = $0.00588
break-even      0.197 / 0.00588                          = 34 requests/day
```

At twenty requests a day the training is the whole bill and prompting wins, by $0.13 to $0.21.
At twenty thousand it is a rounding error and fine-tuning is eleven times cheaper, $11.60 against
$129.00. The same assistant, the same facts, opposite answers — which is why "should we fine-tune"
has no answer without a volume attached.

`t05` is the other end of the same curve: thirty thousand labelled answers at 1,200 tokens is $864
of training, and at a hundred requests a day even the cheap model cannot pay that back.

## 5. The task, step by step

1. Run the baseline. Note that it is right three times, and that two of those are accidents.
2. Write the three cost functions. Check `t02` against the arithmetic above before going further.
3. Add the feasibility rules: a corpus for retrieval; examples, stable facts and no citation
   requirement for a fine-tune.
4. Add the quality filter. Count how many scenarios change answer when you add it.
5. Add the cost comparison and handle the empty set with `none`.
6. Run `sweep.py` and check your per-kind numbers against the table.

Return one of `"prompting"`, `"rag"`, `"finetune"`, `"none"`.

## 6. How you are scored

| metric | weight |
| --- | --- |
| the decision | the accuracy line, target 90% |
| decided by cost | 10 scenarios where every option is possible |
| by constraint | 8 scenarios where at least one option is not |
| bar not met | 6 scenarios where nothing qualifies |
| cost | zero: the drill is arithmetic and calls no model |

The three breakdowns are the diagnosis. A score of 60% concentrated in `bar not met` means you
are not applying the quality filter; the same score concentrated in `by constraint` means the
feasibility rules are missing.

## 7. Done when

- [ ] `python3 run.py --drill w23_finetune --task solutions/w23_reference.py` reports TARGET MET
- [ ] you can compute the break-even volume for a fine-tune from the training cost and the saving
- [ ] you can explain why retrieval cannot win a cost comparison against prompting
- [ ] you can name the three constraints that rule out a fine-tune, and why each one does
- [ ] you can say why `none` is a legitimate answer and which six scenarios it applies to
- [ ] `check_labels.py` passes, including the uniqueness of every cheapest option

## 8. Carry forward

The arithmetic here is the part of the decision that is knowable in advance. The parts that are
not are the parts that usually decide it:

- **Quality is an assumption until you measure it.** Every scenario here hands you the three
  quality numbers. In practice you do not have them, and the honest order is to run `w06`-style
  evals on prompting first, because it is the cheapest experiment, then decide whether retrieval
  or a fine-tune is worth building at all.
- **Latency is absent.** The fine-tuned small model is also faster, which this model does not
  price. `w21` is the drill where that becomes a number.
- **Collection cost is absent.** Labelled examples are free here. They are not free: the 30k
  labels in `t05` are weeks of work, and that work is the real fixed cost of the fine-tune.
- **Vendor lock-in and drift are absent.** A fine-tune is a model you must re-train when the
  vendor deprecates the base model; a retrieval system is an index you must re-embed. Both have
  a maintenance bill that the daily cost does not show.

The one sentence worth taking away: **fine-tuning buys a cheaper request, retrieval buys a
current fact, and prompting buys nothing but is free to try.** The drill is knowing which of
those three you are actually short of.
