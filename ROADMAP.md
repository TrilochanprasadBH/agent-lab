# ROADMAP

What exists, what is missing, and how each gap will be closed.

Two inventories: the Agent Lab (20 drills, in this repository) and the project repos
(all three complete and published). Then the coverage map for the 25
topics, which is the honest answer to "is this all covered".

Last updated: 2026-11-25.

---

## 1. What exists now

| thing | location | state |
| --- | --- | --- |
| Agent Lab, 20 drills | `explore/` | complete, 35 tests passing |
| ragkit, 8 stages | `explore/ragkit/` | complete, 8/8 stages, public repo |
| triage, 7 stages | `explore/triage/` | complete, 7/7 stages, public repo |
| scout, 6 stages | `explore/scout/` | complete, 6/6 stages, public repo |

The lab teaches one idea at a time and grades it. A project teaches composition: eight
stages that end in something you can deploy and defend.

---

## 2. Four delivery forms

Not every topic should become a drill. Choosing the form is part of the design.

**Form A — Lab drill.** Offline, deterministic, under two seconds, one number. Best for
logic, measurement, and decision problems. Anything with a clear right answer that can be
computed on your machine.

**Form B — Project stage.** A module in a multi-stage repo with a runnable product at the
end. Best for system behaviour: retrieval pipelines, agents, services.

**Form C — Design writeup plus a measured simulation.** No production deployment, but a
runnable model of the constraint: queueing, cost arithmetic, capacity planning. Best for
questions that are really about numbers and trade-offs at a scale you cannot host.

There is no Form D. Anything that needs a GPU or a network is out of scope, by decision,
because this folder targets **application-side AI engineering**: retrieval, agents,
evaluation, safety, cost, and shipping. Training weights and running inference servers is
platform work, and it is not what the target roles hire for.

---

## 3. Coverage of the 25 topics

`DONE` means a measured drill or stage exists. `PARTIAL` means a related unit exists but
the specific question is not answered. `GAP` means nothing yet.

| # | topic | status | form | where it goes |
| --- | --- | --- | --- | --- |
| 01 | RAG for 10M documents | PARTIAL | C + B | scale writeup; `scale-rag` project |
| 02 | RAG gives wrong answers, debug it | **DONE** | A | lab w20 (first-failure ladder) |
| 03 | Chunking for legal contracts | PARTIAL | A | new drill: hierarchical, clause-aware |
| 04 | BM25 vs dense vs hybrid | **DONE** | A + B | ragkit stages 02, 04 |
| 05 | Add a reranker and measure it | GAP | B | `ragkit` stage 09; a lab drill was attempted and rejected (section 4) |
| 06 | Cut LLM cost by 70% | PARTIAL | A | new drill: cache + compress + route |
| 07 | First-token latency | GAP | A + C | new drill: simulated stream, TTFT budget |
| 08 | Semantic cache with hit rate | **DONE** | A | lab w16 |
| 09 | Route cheap vs smart model | **DONE** | A | lab w08 |
| 10 | Agent uses tools reliably | **DONE** | A + B | lab w04, w05; `triage` |
| 11 | Agent stuck in a loop | **DONE** | A | lab w05 (a07, a08), w10 |
| 12 | Memory for a long assistant | **DONE** | A | lab w19 (truncate vs summary vs fact ledger) |
| 13 | Always-valid JSON | **DONE** | A | lab w18 (constrained decoding and its blind spot) |
| 14 | Detect and reduce hallucination | PARTIAL | A | new drill: faithfulness scoring |
| 15 | Eval suite for a support bot | **DONE** | A + B | lab w06, w07, w12–w15; ragkit 07 |
| 16 | Trustworthy LLM judge | **DONE** | A | lab w07 |
| 17 | Block prompt injection | **DONE** | A + B | lab w09; `triage` |
| 18 | Redact PII before the model | **DONE** | A | lab w17 |
| 19 | Fine-tune vs RAG vs prompting | GAP | C | decision writeup with cost table |
| 20 | LoRA on 5K examples | OUT OF SCOPE | — | training work, not application work |
| 21 | Serve an open model at scale | OUT OF SCOPE | — | inference infrastructure, not application work |
| 22 | SSE streaming and disconnects | GAP | A | new drill: stream + drop handling |
| 23 | Trace a multi-agent workflow | **DONE** | B | `scout` stage 06; tracing in `triage` stage 05 |
| 24 | Roll back a bad prompt change | PARTIAL | A | new drill: canary + revert decision |
| 25 | Chat for 1M daily users | GAP | C | capacity writeup with arithmetic |

Tally: **13 done, 3 partial, 7 gaps, 2 out of scope.**

Topic 19 stays as a short decision writeup, because choosing between prompting, retrieval
and fine-tuning is an application-side judgment and it comes up in interviews. Topics 20
and 21 are dropped: they are training and serving work, they cannot run in an offline
repository, and they are not what the application-side roles ask for.

---

## 4. The next six, in priority order

Priority is set by hiring weight and by how much the result teaches. Each is a drill
unless stated. The reranker is listed first because it was first in line, not because it is
still the best next move: it has been attempted and rejected for this lab.

### 1. Reranker (topic 05) — attempted, rejected for the lab

Built and measured, then removed: `drills/w16_rerank/` (97 real paragraphs from `docs/` and
the fifteen specs, 16 queries, graded 0/1/2 relevance, nDCG@5, a cross-encoder stand-in with
idf coverage, a synonym table, phrase adjacency and a length prior).

The result, on that collection:

| configuration | nDCG@5 | calls |
| --- | --- | --- |
| first stage (BM25), no rerank | **0.527** | 0 |
| rerank top 6, score only | 0.504 | 96 |
| rerank top 10, score only | 0.472 | 160 |
| rerank top 6, fused with first stage | 0.514 | 96 |
| rerank top 10, fused with first stage | 0.507 | 160 |

Reranking never beat the retriever, and naive reranking made it worse the deeper it looked.
The reason is in the judgments rather than the arithmetic: the queries and the passages that
answer them share little vocabulary ("untrusted document" against "poisoned", "hijacking"
against "instructions"), so a stand-in built out of term statistics has no signal to rank
with. Fixing that by hand-feeding the stand-in a topic lexicon would have meant encoding the
answer key, and a drill that measures its own lookup table teaches nothing.

**This is a result about one simulation, not about reranking.** Real cross-encoders work
because they read the pair; a project without model calls cannot reproduce that.

**What would make it shippable.** Either a real model call in the scoring path (Form A no
longer applies), or a judged collection large enough that the queries use the corpus's own
vocabulary and the lesson becomes ranking rather than semantics — which is `ragkit`'s corpus,
not this lab's. Recorded here so the next session does not rebuild it.

### 2. Semantic cache (topic 08) — DONE as `w16_semantic_cache`

A cache keyed on embedding similarity rather than exact text. Sweep the similarity
threshold and plot hit rate against false-hit rate. The lesson is the threshold, exactly
as in the sufficiency gate.

Why second: cost and latency are the two constraints every team hits, and the trade-off
is easy to measure and hard to guess.

### 3. PII redaction (topic 18) — DONE as `w17_pii`

Detect names, emails, card numbers, and identifiers in text. Report precision and recall
separately, then pick an operating point by which error is worse — the PostHog decision
model, applied to a redaction gate.

Why third: safety work is rarer on portfolios than retrieval work, and this one connects
to a real production pattern with published numbers.

### 4. Constrained JSON (topic 13) — DONE as `w18_constrained_json`

Make a simulated model emit valid JSON every time: schema-constrained decoding, repair,
retry, and a fallback. Score validity rate, retries per request, and latency cost. Extends
lab drill w01 from "repair" to "prevent".

### 5. Memory (topic 12) — DONE as `w19_memory`

Six 60-turn conversations, a 160-token memory budget, 78 probes. Truncation retains 30.8% and
answers 26.9% of the rest with a value the customer never gave. A rolling summary reaches 56.4%
and silently rewrites numbers. A twelve-fact ledger keeps 92.3% in 32 tokens and misses the one
detail no schema anticipated; the ledger plus the last six turns keeps 100% in 87 tokens.
Correction handling alone is worth 15 points: first match 84.6%, last match 92.3%, skip a negated
mention 100%.

### 6. Debug the wrong answers (topic 02) — DONE as `w20_debug`

42 failing questions over seven stages (ingestion, chunking, query, retrieval, packing,
generation, stale), each with a full trace. "Blame the model" scores 14.3%; a score heuristic
21.4%; every check but in the wrong order 35.7%; the first-failure ladder 100%. All 42 look
identical from the outside and the retrieval score is at or above 0.85 in all 42.

---

## 5. The two projects

**`triage` (7 stages).** Support agent: classify, retrieve policy, draft, escalate.
Covers tools with approval gates, audit trails, trajectory eval, PII handling, and
tracing. This is the repo that answers topics 10, 11, 15, 17, and 23 in one system.

**`scout` (6 stages).** Research agent: plan, search, read, synthesise with citations.
Covers sub-agents, budget control, citation accuracy, and multi-agent tracing. Topics 23
and part of 07.

---

## 6. Out of scope, by decision

| topic | why it is out | where it belongs instead |
| --- | --- | --- |
| 20. LoRA fine-tuning | needs a GPU; training is not application work | a dedicated training project, or a course |
| 21. Serving an open model | needs a GPU and an infra surface | an MLOps or platform track |

Topic 19 is the exception: "fine-tune vs RAG vs prompting" is a decision an application
engineer is expected to make and defend, so it stays as a short writeup with the cost
arithmetic for each option. Knowing when *not* to fine-tune is the skill; doing the
fine-tuning is a different job.

---

## 7. How a new topic becomes a unit

1. Decide the form with section 2. If a topic cannot be graded, it is a writeup, not a
   drill.
2. Write the failing test first. If you cannot write a test, the goal is not defined yet.
3. Build the reference. Measure it against a baseline.
4. Write the lesson in the format fixed by `AGENTS.md` section 4 or 5.
5. If the measurement contradicts a published claim, say so in `FIELD-NOTES.md`.
6. Record the number in the README and the roadmap.

A topic that skips step 2 is a blog post.
