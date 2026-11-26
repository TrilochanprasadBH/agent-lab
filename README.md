# Agent Lab

Twenty-one practice drills for building AI agents and for measuring whether they work.

Every drill is a small program that runs offline in about two seconds. You edit one
file, run one command, and get a number that says how well you did.

---

## 1. What this is

This repository teaches the engineering around a language model. It does not teach
how to train a model. It teaches what to do after you have a model:

- how to get the right text in front of it
- how to let it call tools safely
- how to run it in a loop without it running away
- how to measure whether any of it improved
- how to keep it cheap, safe, and debuggable

Each drill isolates one of those problems. The problems are isolated on purpose: if
one thing is wrong at a time, the number tells you what it was.

## 2. What you will be able to do afterwards

By the end of drill 21 you will be able to:

1. Build a retrieval system and measure its quality with a number.
2. Fit evidence into a fixed context budget without losing the part that matters.
3. Turn unreliable model output into validated tool calls.
4. Write an agent loop with correct termination, including giving up.
5. Write an eval set, a grader, and a judge, and know the failure modes of each.
6. Decide whether a measured improvement is real or noise.
7. Gate a release on per-category results instead of an average.
8. Put a threshold on a similarity score, and justify it from what each error costs.
9. Redact personal data with separate numbers for leaks and over-redaction.
10. Make model output schema-valid, and separate validity from correctness.
11. Keep the facts that matter when a conversation outgrows its context budget.
12. Debug a wrong answer to the stage that actually lost the evidence.
13. Serve a latency budget by finding the bottleneck in requests per second.
14. Defend an AI system's reliability in a technical conversation.

## 3. Requirements

- Python 3.10 or newer (`python3 --version`)
- A terminal
- Nothing else: no API key, no network, no third-party packages

The lab was built and tested on Python 3.15 on macOS. It uses only the standard
library.

## 4. First run

From the root of this repository:

```sh
python3 run.py --list
```

That prints every drill with its target. Then:

```sh
python3 run.py --drill w01_extraction
```

You will see a scorecard. It will fail. That is expected: the scorecard is scoring
the starting code, not you.

## 5. How a drill works

Every drill follows the same five steps.

```
Step 1  Read the brief               drills/wNN_*/spec.md
Step 2  Run the starting code        python3 run.py --drill wNN_*
Step 3  Edit the task file           drills/wNN_*/task.py
Step 4  Run it again                 python3 run.py --drill wNN_*
Step 5  Stop when the target is met  the card says TARGET MET
```

Three files matter to you:

| file | you should |
| --- | --- |
| `drills/wNN_*/spec.md` | read it first, once, completely |
| `drills/wNN_*/task.py` | edit this; it is the only file you change |
| `solutions/wNN_reference.py` | read it only after you have tried |

Everything else is fixed. `agentlab/` is the machinery that runs and scores; you
read it to understand the scoring, you do not change it.

## 6. Reading the scorecard

```
 accuracy       70.8%   target 90%   [FAIL]
```

`accuracy` is the drill's main measure. Each drill defines it exactly in its spec.
It is always a fraction between 0 and 1 shown as a percentage.

```
 cost          $0.0051   cap    $0.0120   [PASS]
```

Every model call has a token price. `cost` is what your run would have cost at real
prices. The cap is the budget. A solution that is accurate but over budget fails.

```
 crashes            0   allowed 0   [PASS]
```

If your code raises an exception, that is a crash. Crashes are always failures. The
harness catches them so that one bad item does not stop the run.

```
 model calls     1.00/doc   min 0.9   [PASS]
```

How many model calls you made per item. Some drills require you to actually use the
model, so bypassing it fails.

```
 metrics
   vendor              68.8%  ███████████████████.........
```

The per-field or per-metric breakdown. This is where you find what is wrong.

```
 failure modes
    13x  vendor: missing / null
```

Failures grouped by cause. Fix classes of failures, not individual items.

```
 next move
 - Model output is often not valid JSON. Repair it before you trust it.
```

The harness reads your failure pattern and suggests the next thing to try. It is a
hint, not an answer.

## 7. The drills

Twenty-one drills in five groups. The groups are ordered: each assumes the previous.

### Group A: getting the right text to the model

| # | drill | goal | baseline → reference | target |
| --- | --- | --- | --- | --- |
| 01 | schema repair | extract structured data from messy model output | 70.8% → 99.5% | 90% |
| 02 | retrieval | find the right document for a question | 71.7% → 96.7% | 88% |
| 03 | context packing | fit the needed evidence into a token budget | 11.1% → 94.4% | 90% |

### Group B: letting the model act

| # | drill | goal | baseline → reference | target |
| --- | --- | --- | --- | --- |
| 04 | tool calls | turn text into validated, authorised tool calls | 10.7% → 100% | 90% |
| 05 | agent loop | run a multi-step task to a correct stop | 20.0% → 100% | 90% |
| 09 | injection defence | read untrusted documents without obeying them | 0.0% → 100% | 95% |

### Group C: measuring

| # | drill | goal | baseline → reference | target |
| --- | --- | --- | --- | --- |
| 06 | evals | write a grader that generalises to unseen data | 50.0% → 100% | 90% |
| 07 | judge calibration | get reliable preferences out of a noisy judge | 66.7% → 100% | 85% |
| 10 | trace triage | name the root cause of an agent failure | 18.3% → 100% | 90% |
| 12 | significance | decide whether a score change is real | 60.0% → 94.3% | 90% |
| 13 | eval sets | build a sample that covers what matters | 31.2% → 100% | 90% |
| 14 | trajectory eval | apply a rubric to a full agent run | 42.9% → 100% | 85% |
| 15 | regression gating | catch a release that improves the average and breaks a category | 63.3% → 100% | 90% |
### Group D: shipping and operating

| # | drill | goal | baseline → reference | target |
| --- | --- | --- | --- | --- |
| 08 | routing | hit an accuracy target under a cost cap | 100% but over budget → 100% in budget | 92% |
| 16 | semantic cache | reuse an answer without serving it to the wrong question | 0.0% → 74.2% | 68%, wrong hits under 5% |
| 17 | PII redaction | redact personal data without shredding the message | 0.0% → 97.7% | 93% recall, precision ≥ 90% |
| 18 | constrained JSON | get valid objects without losing what is in them | 0.0% → 86.7% | 82% correct, validity ≥ 99% |
| 19 | memory | keep the facts that matter under a fixed context budget | 30.8% → 100% | 85% |
| 20 | debug a wrong answer | name the stage that lost the evidence, not the symptom | 14.3% → 100% | 90% |
| 21 | first-token latency | meet a latency, quality and cost budget at 40 rps | 0.0% → 95.8% | 92%, p95 ≤ 900ms, $0.0008 |

### Group E: putting it together

| # | drill | goal | baseline → reference | target |
| --- | --- | --- | --- | --- |
| 11 | capstone | satisfy ten requirements in one pipeline | 20.8% → 100% | 90% |

## 8. Recommended order

Work in numeric order. The numbers were assigned in dependency order, not topic
order.

```
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21
```

Two exceptions worth knowing:

- **Drill 08** only teaches cost. It is safe to move later if you prefer.
- **Drill 11** is the composition drill. Leave it for last. It assumes 01 through 09.

## 9. How to use this with two hours a week

Two sessions per week is enough.

**Session A, about 75 minutes.**

1. Read the spec once, completely, before touching code. Ten minutes.
2. Run the starting code. Look at the failure modes for two minutes.
3. Make one change. Run. Read the number.
4. Make one more change. Run. Stop even if you have not reached the target.

**Session B, about 45 minutes.**

1. Run again. Confirm the number is the same. If it is not, you changed something
   you did not mean to.
2. Finish the drill, or write down why you are stuck.
3. Fill in the entry in `progress.md`. Four lines is enough.

The written note is the part that makes it stick. Without it you will solve the
same class of problem three times and not notice.

## 10. Vocabulary

AI engineering has a lot of names for a small number of ideas. `docs/glossary.md`
defines every term used in this repository in one or two sentences.

The eight you need before drill 01:

| term | meaning |
| --- | --- |
| model | a function that takes text and returns text |
| prompt | the text you give the model |
| context window | the maximum amount of text the model can consider at once |
| token | the unit models count text in, roughly three quarters of a word |
| tool call | a structured request from the model to run a function |
| agent | a loop that calls a model, runs tools, and feeds results back |
| eval | a repeatable test that scores output against expected behaviour |
| ground truth | the correct answer, known in advance, used to score |

## 11. Running a drill against a real model

Only drill 01 supports this. The other fourteen are deterministic worlds, and a
real model would change the ground truth rather than the lesson.

```sh
export OPENROUTER_API_KEY=sk-or-...
python3 run.py --drill w01_extraction --provider openrouter --model <model-id> --limit 5
```

Read `docs/real-models.md` before spending money. It covers cost, caching,
determinism, and how to add another provider.

## 12. Checking the lab itself

```sh
python3 -m unittest discover -s tests -v
```

These tests verify that the lab is still fair: every starting point must fail,
every reference solution must pass, and every score must be reproducible. If you
change the harness and a drill becomes unsolvable, these tests catch it.

## 13. Adding a drill

Create a directory `drills/wNN_name/` containing five files:

| file | purpose |
| --- | --- |
| `data.py` | the items, generated deterministically, with ground truth |
| `task.py` | the starting code the learner edits |
| `drill.py` | configuration and the scoring function |
| `spec.md` | goal, background, steps, scoring, done criteria |
| `__init__.py` | empty |

`drill.py` must define:

```python
NAME             str    # shown in the header
PREMISE          str    # one line, shown in the header
TARGET_ACCURACY  float  # the pass threshold
MAX_COST_USD     float  # the budget
SUPPORTS_REAL    bool   # whether --provider openrouter is allowed
TASK_NAME        str    # the function in task.py the learner implements

def corpus() -> list: ...            # the items to run
def build_model(seed: int): ...      # the model or world
def score(results, model, target_accuracy, max_cost_usd) -> Scorecard: ...
```

Add the drill name to `DRILLS` in `tests/test_drills.py`, add its row to the
table in section 7, and add it to `progress.md`. The tests then check three
things: your baseline fails, your reference passes, and both numbers match the
table. If you change a drill, the table has to change with it — that is
`tests/test_documented_numbers.py`, and it is the reason the numbers in this
README can be trusted.

## 14. Repository layout

```
agentlab/              the harness, shared by every drill
  model.py             a simulated model that fails in realistic ways
  providers.py         provider interface: simulated, scripted, OpenRouter
  tools.py             schema-validated tool registry with a confirmation gate
  evals.py             normalization, field scoring, scorecard
  drill.py             runs a task over a corpus
drills/                twenty-one drills, each self-contained
solutions/             one reference solution per drill
tests/                 checks that the lab is fair and reproducible
docs/                  glossary and real-model notes
run.py                 the entry point
progress.md            your written log
```
