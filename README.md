# Agent Lab

Fifteen drills for agent engineering — ten components, a capstone, and four on evaluation. Each is a seeded world with hidden ground truth, a deliberately mediocre baseline, and a numeric target. You edit one file. The harness scores you in about a second and shows you your top failure modes.

No API keys. No network. No setup once the lab exists.

## Why this shape

Reading about evals does not make you good at evals, any more than reading about swimming makes you a swimmer. What changes you is a repeated loop with a fast, honest signal:

```
   read the brief  ->  change one thing  ->  see the number move  ->  write it down
```

That loop has to fit in a session, or it does not happen. This one runs in two seconds.

Every drill below exists because it has a *number* attached — not because it is an interesting topic. If you cannot measure it, it is a book club, not practice.

## Quick start

```sh
python3 run.py --list                          # what is here
python3 run.py --drill w02_retrieval           # score your attempt
python3 run.py --drill w02_retrieval --failures 10   # see what is actually breaking
python3 run.py --drill w02_retrieval --trace out.jsonl
python3 run.py --drill w01_extraction --task solutions/w01_reference.py   # a passing version
python3 -m unittest discover -s tests -v       # check the lab itself
```

Start with `w01`, then work in order. Later drills assume the earlier habits. Leave `w11` for last — it is the exam.

## The ten

| # | drill | the number you move | baseline → reference |
|---|---|---|---|
| 01 | schema repair & verification | field accuracy under a cost cap | 70.8% → 99.5% |
| 02 | retrieval from scratch | recall@3 and first-hit | 71.7% → 96.7% |
| 03 | context packing under a budget | evidence coverage in 120 tokens | 11.1% → 94.4% |
| 04 | tool schemas & malformed arguments | correct outcome, zero unsafe calls | 10.7% → 100% |
| 05 | the agent loop | success inside a step budget | 20.0% → 100% |
| 06 | evals that resist overfitting | agreement on a hidden split | 50.0% → 100% |
| 07 | judge calibration | agreement per dollar | 66.7% → 100% |
| 08 | routing and cost | accuracy under a hard cap | 100% but $0.060 → 100% at $0.0275 |
| 09 | injection defence | correct answers, zero exfiltration | 0.0% → 100% |
| 10 | trace triage | correct root cause | 18.3% → 100% |
| 11 | **capstone** | tickets handled *and* nothing unsafe | 20.8% → 100% |
| 12 | is the difference real? | correct ship / no-ship decisions | 60.0% → 94.3% |
| 13 | designing an eval set | cell coverage, no duplicate sources | 31.2% → 100% |
| 14 | trajectory evaluation | rubric agreement within 1 point | 42.9% → 100% |
| 15 | regression gating | no false ships | 66.7% → 100% |

What each one is actually teaching:

1. **Schema repair** — the model is not the fixable part. Repair, normalise, validate against arithmetic and against the source, retry only on a detected defect.
2. **Retrieval** — IDF weighting, stemming, alias expansion, title and phrase boosts. Thirty lines that beat an embedding model on a small corpus.
3. **Packing** — a context window is a budget. Selection is a covering problem, not a ranking problem.
4. **Tools** — most agent bugs live in the twenty lines between "the model returned text" and "the tool ran". Confirmation is a human act, not a model opinion.
5. **The loop** — the model has no memory. Anything it knows, you put there. Including that it is stuck.
6. **Evals** — the train set is rigged with spurious correlations. A grader fitted to one sample of writers is not a model of quality.
7. **Judges** — position bias is systematic and fixable by swapping. Noise is random and only outvoted. A deterministic judge given an identical prompt is not a new sample.
8. **Routing** — accuracy without a cost line is a demo. Route by shape, then by stakes, then by measured confidence.
9. **Injection** — retrieved text is untrusted input. Sanitise in, label the boundary, and gate tools on the way out.
10. **Triage** — read the primary error line, order your rules by specificity, resist adding a keyword per case.
11. **Significance** — pairing, McNemar, and the one check that comes before any statistic: were these two runs even evaluated on the same items?
12. **Eval sets** — an eval set is a sample. Missing cells make it blind; duplicate sources make it smaller than it looks.
13. **Trajectory eval** — safety gates override, outcome scores, process penalises, floor at zero. Most rubric bugs are precedence bugs.
14. **Regression gating** — never gate on a single number. The worst slice is where the incident comes from.
15. **Capstone** — twelve tickets, ten requirements, one pipeline. Retrieval, sanitising, validation, gating, observation, loop bounds, grounding, and stopping well, simultaneously. The baseline is *cheaper* than the correct answer, which is the honest trade.

## Simulated by default, real when you want it

Every drill runs against a simulated model: deterministic, offline, instant, free. That is what makes a two-second feedback loop possible, and it is where the systems discipline gets built — the simulator fails in the ways models characteristically fail, so your wrapper has to be genuinely defensive.

Drill 01 also runs against a real model behind the same interface:

```sh
export OPENROUTER_API_KEY=sk-or-...
python3 run.py --drill w01_extraction --provider openrouter --model <model-id> --limit 5
```

Responses are cached on disk, so an unchanged attempt costs nothing to rerun. See `docs/real-models.md` for costs, noise, and how to add another provider.

The other nine are deterministic worlds — a real model would change the ground truth, not the lesson — and the harness refuses `--provider` for them rather than pretending.

## How a drill is scored

| line | meaning |
|---|---|
| accuracy | the drill's headline metric, or the mean of its metrics |
| cost | what your calls would have cost in real tokens |
| crashes | exceptions your task raised; must be zero |
| model calls | calls per item; a bypass is not a solution |
| latency p95 | from the simulated model |
| failure modes | clustered by kind, so you fix classes not instances |

Normalization is deliberately forgiving. `"1.350,00 EUR"` and `1350.00` are the same money, `"12 March 2026"` is a valid date. You are judged on whether you understood the problem, not on whether you guessed the serialization.

## The loop, weekly

At 2–3 hours a week, the rhythm that works is two sessions:

**Session A (about 90 minutes)** — read the brief, run the baseline, make one substantial change, look at failures, make one more. Stop while you still have a clear next move.

**Session B (about 45 minutes)** — rerun, try a different seed where the drill supports it, run the tests, then write the retro in `progress.md`.

The retro is not bookkeeping. It is the difference between ten drills that taught you one lesson and ten drills that taught you ten.

## Adding a drill

A drill is a directory under `drills/` with five files:

```
drills/wNN_name/
    data.py     seeded corpus, each item carrying its ground truth
    task.py     the file the learner edits; starts deliberately weak
    drill.py    NAME, TARGET_ACCURACY, MAX_COST_USD, TASK_NAME, corpus(), build_model(), score()
    spec.md     the brief, with the reasoning and a "done looks like" list
```

`solutions/wNN_reference.py` proves it is solvable. `tests/test_drills.py` will then check the new drill automatically: the baseline must fail, the reference must pass, and both scores must be deterministic.

## Still ahead

Ten is a term, not a year. The next ten, in the order they become useful:

| # | drill | the number |
|---|---|---|
| 16 | memory and compression | fact retention after summarisation |
| 17 | parallel fan-out | quality per unit of cost |
| 18 | observability and replay | deterministic reproduction of a trace |
| 19 | regression-safe iteration | shipped changes with zero regressions |
| 20 | streaming and partial results | perceived latency |
| 21 | long-context retrieval | needle accuracy at 100k tokens |
| 22 | constrained output | schema-valid rate, zero retries |
| 23 | self-consistency vs cost | accuracy bought per dollar |
| 24 | multi-agent: when it helps | quality per unit of cost |

Drills get built when you reach them, not all at once. A curriculum written in advance is a fantasy; a curriculum that grows from this week's failures is a plan.

## Layout

```
agentlab/          the harness — read it, do not edit it
  model.py         deterministic flaky model with token accounting
  providers.py     provider seam: simulated, scripted, OpenRouter, your own
  tools.py         schema-validated tool registry with a confirmation gate
  evals.py         normalization, field scoring, failure clustering
  drill.py         corpus runner
drills/            ten drills, each with data, task, drill, spec
solutions/         reference solutions, after you have tried
tests/             checks that the drills are fair and solvable
docs/              notes on running against real models
run.py             the runner
progress.md        your retro log
```
