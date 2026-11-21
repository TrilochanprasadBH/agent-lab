# Agent Lab

A drill lab for agent engineering: small, seeded exercises with hidden ground
truth, a deliberately mediocre baseline, and a numeric target. You edit one
file. The harness scores you in about a second and shows you your top failure
modes.

No API keys. No network. No setup once the lab exists.

## Why this shape

Reading about evals does not make you good at evals, any more than reading about
swimming makes you a swimmer. What changes you is a repeated loop with a fast,
honest signal:

```
   read the brief  ->  change one thing  ->  see the number move  ->  write it down
```

That loop has to fit in a session, or it does not happen. This one runs in two
seconds.

## Quick start

```sh
python3 run.py                          # score your current attempt
python3 run.py --failures 10            # see what is actually breaking
python3 run.py --seed 11                # check you did not tune to one seed
python3 run.py --task solutions/w01_reference.py   # see a passing version
python3 -m unittest discover -s tests -v
```

The first run scores the baseline at about **71%** against a **90%** target.

## How a drill is scored

| line | meaning |
|---|---|
| accuracy | mean over four fields: vendor, date, currency, total |
| cost | what your model calls would have cost in real tokens |
| crashes | exceptions your task raised; must be zero |
| model calls | how many calls per document; a bypass is not a solution |
| latency p95 | informational, from the simulated model |
| failure modes | clustered by field and cause, so you fix classes not instances |

Normalization is deliberately forgiving — `"1.350,00 EUR"` and `1350.00` are the
same money, `"12 March 2026"` is a valid date. You are judged on whether you
understood the document, not on whether you guessed the serialization.

## The loop, weekly

At 2–3 hours a week, the rhythm that works is two sessions:

**Session A (about 90 minutes)** — read the brief, run the baseline, make one
substantial change, look at failures, make one more. Stop while you still have a
clear next move.

**Session B (about 45 minutes)** — try a second seed, run the tests, then write
the retro in `progress.md`: what you changed, which number moved, what surprised
you, and what you would try next.

The retro is not bookkeeping. It is the difference between ten drills that
taught you one lesson and ten drills that taught you ten.

## Adding a drill

A drill is a directory under `drills/` with four files:

```
drills/wNN_name/
    data.py     seeded corpus, each item carrying its ground truth
    task.py     the file the learner edits; starts deliberately weak
    drill.py    NAME, TARGET_ACCURACY, MAX_COST_USD, build()
    spec.md     the brief, with a hint ladder
```

`drill.py` must expose `build(seed) -> (corpus, model)` and `get_task()`. The
corpus items need `.doc_id`, `.raw`, and `.truth`; scoring reads `truth` per
field. Add the field list to `agentlab/evals.py:SCORED_FIELDS` if a drill scores
something other than the invoice fields.

## Roadmap

One drill every two weeks is 26 in a year, which is more than 130 hours can
honestly absorb. Twenty is the realistic target. Each row is a skill that shows
up in real agent work, chosen because it has a number attached.

| # | drill | the number you move |
|---|---|---|
| 01 | schema repair & verification | field accuracy under a cost cap |
| 02 | retrieval from scratch | recall@k on a seeded corpus |
| 03 | chunking under a token budget | answer accuracy at fixed context size |
| 04 | tool schemas & malformed arguments | valid-call rate |
| 05 | the agent loop | task success within a step budget |
| 06 | writing evals that resist overfitting | held-out accuracy |
| 07 | judge calibration | agreement with human labels |
| 08 | caching and routing | cost at fixed quality |
| 09 | failure taxonomy from traces | root causes found per hour |
| 10 | injection defence in retrieved text | attack success rate |
| 11 | constrained output | schema-valid rate, zero retries |
| 12 | memory and compression | fact retention after summarization |
| 13 | parallelism: when it helps | quality per unit of cost |
| 14 | observability and replay | reproduce a trace deterministically |
| 15 | regression-safe iteration | shipped changes with no regressions |
| 16 | streaming and partial results | perceived latency |
| 17 | reproducibility of stochastic failure | failure rate reproduced |
| 18 | long-context retrieval | needle accuracy at 100k tokens |
| 19 | self-consistency vs cost | accuracy bought per dollar |
| 20 | capstone | an end-to-end agent plus a published eval report |

Drills get built when you get to them, not all at once. A curriculum written in
advance is a fantasy; a curriculum that grows from this week's failures is a
plan.

## Layout

```
agentlab/          the harness — read it, do not edit it
  model.py         deterministic flaky model with token accounting
  evals.py         normalization, field scoring, failure clustering
  drill.py         corpus runner
drills/            one directory per drill
solutions/         reference solutions, after you have tried
tests/             checks that the drills are fair and solvable
run.py             the runner
progress.md        your retro log
```
