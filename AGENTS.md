# AGENTS.md — how to work in this folder

This file exists so that a new session can continue without re-deriving anything. Read
it fully before creating or changing a repository here.

Last updated: 2026-11-24.

---

## 1. What lives here

```
~/Desktop/explore/            the parent folder
  AGENTS.md                   this file: rules and conventions
  ROADMAP.md                  what is built, what is next, coverage of the 25 topics
  WORKSPACE.md                which folder is which repository
  README.md                   the Agent Lab: 18 drills
  run.py                      lab entry point
  agentlab/                   lab harness
  drills/  solutions/  tests/ the lab's content
  docs/                       lab glossary and real-model notes

  ragkit/                     project 1, own git repo, 8 stages, COMPLETE
  triage/                     project 2, 7 of 7 stages, COMPLETE
  scout/                      project 3, 6 stages, COMPLETE
```

Each project folder is its **own git repository**, nested inside `explore` so everything
sits in one place. Every project folder is listed in `explore/.gitignore`, so the parent
repository never tracks them.

---

## 2. Rules that are not negotiable

**Everything runs offline.** No network at run time, no API keys required, no third-party
packages. Python standard library only. This is what makes the material usable by anyone,
anywhere, and it is the reason the projects can be cloned and run in one command.

**Python 3.10 or newer.** Developed on 3.15 on macOS. Use `from __future__ import
annotations` in every module.

**Every number is measured, never asserted.** If a document claims a technique helped,
there is a run that produced the number. If it did not help, say so and keep the
measurement.

**Every technique gets a baseline comparison.** Never "we added X". Always "with X and
without X, here are both numbers".

**Determinism.** Same input, same output, every run. Seed every generator. Sort before
iterating over files. A score change must mean a code change.

**No real model calls in the graded path.** Model behaviour is simulated or scripted. The
one exception is `ragkit`'s optional `remote` embedder, which is documented and off by
default.

---

## 3. Quality bar for a stage or a drill

A unit of work is not done until all of these are true:

1. A **stub** exists that raises `NotImplementedError` with a docstring that states the
   contract precisely.
2. A **reference implementation** exists and passes every test.
3. **Tests** are executable with one command and fail on the stub, pass on the reference.
4. A **lesson** is written in the eight-section format below.
5. A **number** appears in the project README and in `GUIDE.md`.
6. `python scripts/status.py` reports it passing.

If any of the six is missing, the work is not finished, no matter how good the code is.

---

## 4. Lesson format (projects)

Every `stages/NN_name/README.md` uses exactly these sections, in this order:

```
# Stage NN — Title
   (one command to run the tests)
## What you will build          one sentence
## Why this step is next        what breaks without it, tied to the previous number
## The idea                     first principles, definitions, formulas, no hand-waving
## The measurement              optional: the table produced by the eval, with intervals
## Field notes                  what production teams published; cite; say what we did NOT do
## Do this                      numbered tasks with exact filenames
## Check yourself               the commands and the expected output
## If you are stuck             three hints, least revealing first
## What a senior would notice   judgment: what separates correct from good
```

`Field notes` is required in every lesson, even when the entry is short. `The measurement`
is optional and belongs before the field notes, so a reader meets the result before the
industry context.

Rules for the prose:

- short sentences, declarative, no rhetorical flourishes, no "here's the thing"
- define a term the first time it appears
- show the formula or the mechanism, not just its name
- state the limitation of the technique in the same section that introduces it
- never imply a result you did not measure

## 5. Lesson format (lab drills)

`drills/wNN_name/spec.md` uses the condensed version:

```
Goal / Outcome / Target / Time     a four-line table
1. Why this drill exists
2. What you are given
3. How to run it
4. Background: the idea from first principles
5. The task, step by step
6. How you are scored
7. Done when (checklist)
8. Carry forward
```

`drills/wNN_name/task.py` opens with a docstring containing: **Goal**, **Return**, **Run**,
**Starting point**, **Full brief**.

---

## 6. Repository conventions (projects)

```
<project>/
  README.md          what it is, quick start, results table (numbers, not adjectives)
  GUIDE.md           the course: stage table, how to work, the sentence each stage earns
  FIELD-NOTES.md     sourced notes on production practice, plus "what we did not build"
  NOTES.md           the learner's log, three lines per stage
  stages/NN_name/
    README.md        the lesson
    test_stageNN.py  executable specification
  src/<pkg>/         learner workspace: stubs with contracts
  reference/<pkg>/   complete implementation, same module names
  evals/             golden sets and runners
  scripts/           status.py, bench.py, serve.py, fetch helpers
  corpus/            vendored real data, with its licence
  Dockerfile         optional, for stages that ship
```

**The `IMPL` convention.** Tests and scripts read `IMPL` from the environment and put
either `src` or `reference` on `sys.path`:

```sh
python stages/03_analysis/test_stage03.py              # your code
IMPL=reference python stages/03_analysis/test_stage03.py   # the answer
```

Every project has `scripts/status.py`, which runs each stage's tests in a subprocess and
prints one line per stage. This is the first command in any session.

**Each stage adds a module; it does not rewrite one.** This keeps the history additive,
keeps earlier tests passing, and lets the learner diff stage by stage.

---

## 7. Evaluation conventions

- A **golden set** is a file of questions, each with a verifiable gold label (usually a
  phrase that must appear in the source). Verify every label programmatically before
  trusting it.
- **Label by phrase, not by chunk id**, so labels survive re-chunking.
- **Hold out a split.** Development questions are for tuning; the test split is looked at
  once. Record the split in the data file so it cannot be quietly changed.
- **Every proportion carries a Wilson interval.** Report it next to the number.
- **Every documented number has a check.** Run the project's `evals/check_docs.py` after
  changing code; if a number moved, the documents that quote it must move with it. Drift
  here is the failure mode this folder is most exposed to. The lab's version is
  `tests/test_documented_numbers.py`: it parses the drill table in `README.md`, runs every
  drill twice, and fails on a mismatch.
- **Every comparison between two configurations is paired** and tested with exact
  McNemar. Report the discordant counts, not just the p-value.
- **Run a power calculation** before claiming a small difference matters.
- **Report the errors separately.** False answers and false refusals cost different
  things; one blended accuracy number hides which one you bought.

---

## 8. Field notes conventions

`FIELD-NOTES.md` accumulates entries in this exact shape:

```
### N. Short title — source, date
**Source.** URL
**What they did.** two to five sentences, with the numbers they published
**What it means.** the transferable lesson
**In this project.** what we do, and what we deliberately do not do
```

Rules:

- cite only what you actually read; never inflate a claim
- include the results that contradict the vendor when you find them (the 2026
  contextual-retrieval replication is the model for this)
- end each entry with what was **not** built here, and when you would build it
- keep the closing table "what we deliberately did not build" up to date

---

## 9. Git and GitHub

- One repository per project, initialised inside `explore/<project>/`.
- Add the project folder to `explore/.gitignore` immediately, so the parent repo stays a
  lab and does not nest repositories.
- Commit messages: a short imperative subject, then a body of bullets describing what was
  built and the measured result. Example from ragkit:

```
Stage 04: dense retrieval and rank fusion, with the negative control

- three embedders behind one interface
- hybrid 87.5% recall@5 vs 83.3% lexical; dense alone was worse than lexical
- the weak embedding made hybrid worse than lexical alone (75.0%)
```

- **Never delete a branch**, locally or remotely.
- Pushing to the personal account uses the personal token explicitly, so the global `gh`
  active account is not changed:

```sh
GH_TOKEN=$(gh auth token --user TrilochanprasadBH) gh repo create <name> --public \
  --source=. --remote=origin --push --description "..."
```

- Keys come from environment variables only, never from command-line flags.

---

## 10. Data and corpora

- Vendor a **real** corpus, not invented prose, whenever the exercise is about text. Real
  documents have the awkwardness that makes the exercise worthwhile.
- **Exception: label-sensitive exercises.** When the exercise depends on exact, known
  ambiguities that no public corpus contains (a support taxonomy where "cancel my order" and
  "cancel my subscription" must be separated), an authored corpus is allowed, and the README
  must say so and why. The labels are then the artefact, so they need
  `evals/check_labels.py` verifying them.
- Record the licence next to the data (`corpus/<name>/LICENSE`).
- Keep it small enough to clone quickly (ragkit is 264 KB, 22 files).
- If a larger corpus would help, write a `scripts/fetch_corpus.py` that downloads it, and
  keep the vendored sample as the offline default.

---

## 11. Writing rules that apply everywhere

1. **Goal first, then mechanism, then steps.** Never state a conclusion before the
   evidence that supports it.
2. **Define every term** the first time it appears. If a spec uses a word the glossary
   does not define, that is a bug.
3. **Show the arithmetic.** "Two points" needs its denominator and its interval.
4. **State the limitation in the same breath as the technique.** A technique presented
   without its failure mode teaches half a skill.
5. **Report null results.** A measured "this did not help" is worth more than an
   unmeasured "this is best practice".
6. **No adjectives doing the work of numbers.** "Significantly better" is banned;
   "4.2 points better on 24 held-out questions, p = 0.03" is required.

---

## 12. Starting a new session

Do this in order:

1. Read this file, then `ROADMAP.md`, then the project's `GUIDE.md`.
2. `cd <project> && python scripts/status.py` — see which stages pass.
3. Read the most recent `git log --oneline -5` in the project and in the lab.
4. Check `FIELD-NOTES.md` for what has already been researched; do not re-research it.
5. Pick the next unit from `ROADMAP.md`, not from imagination.
6. Follow sections 3–7 above without exception.

If a request conflicts with the quality bar in section 3, say so before starting.

---

## 13. Session history in one paragraph

The lab started as fifteen drills covering extraction, retrieval, packing, tools, loops,
evaluation, judges, routing, injection, triage, and a capstone. `ragkit` then turned the
first four of those into one coherent product across eight stages, ending with a served
endpoint and an eval report that states what it cannot yet prove. The recurring habit
throughout: build the smallest honest version, measure it against a baseline, write down
what happened including the failures, and treat the eval set as the real bottleneck. The
three findings worth remembering: a weak retriever made a hybrid system worse than lexical
alone; heading weighting did nothing on a real corpus; and the held-out split exposed 29
points of optimism in the development numbers.
