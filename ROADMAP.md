# ROADMAP

What exists, what is missing, and how each gap will be closed.

Two inventories: the Agent Lab (23 drills, in this repository) and the project repos
(all three complete and published). Then the coverage map for the 25
topics, which is the honest answer to "is this all covered".

Last updated: 2026-11-25.

---

## 1. What exists now

| thing | location | state |
| --- | --- | --- |
| Agent Lab, 23 drills | `explore/` | complete, 35 tests passing |
| ragkit, 9 stages | `explore/ragkit/` | complete, 9/9 stages, public repo |
| triage, 9 stages | `explore/triage/` | complete, 9/9 stages, public repo |
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
| 05 | Add a reranker and measure it | **DONE** | B | ragkit stage 09 (measured, not shipped) |
| 06 | Cut LLM cost by 70% | PARTIAL | A | new drill: cache + compress + route |
| 07 | First-token latency | **DONE** | A + C | lab w21 (queueing simulation, three gates) |
| 08 | Semantic cache with hit rate | **DONE** | A | lab w16 |
| 09 | Route cheap vs smart model | **DONE** | A | lab w08 |
| 10 | Agent uses tools reliably | **DONE** | A + B | lab w04, w05; `triage` |
| 11 | Agent stuck in a loop | **DONE** | A | lab w05 (a07, a08), w10 |
| 12 | Memory for a long assistant | **DONE** | A | lab w19 (truncate vs summary vs fact ledger) |
| 13 | Always-valid JSON | **DONE** | A | lab w18 (constrained decoding and its blind spot) |
| 14 | Detect and reduce hallucination | PARTIAL | A | new drill: faithfulness scoring |
| 15 | Eval suite for a support bot | **DONE** | A + B | lab w06, w07, w12–w15; ragkit 07 |
| 16 | Trustworthy LLM judge | **DONE** | A + B | lab w07; `triage` stage 08 (κ measured against authored human golds) |
| 17 | Block prompt injection | **DONE** | A + B | lab w09 (the drill); `triage` adversarial set — 3/3 injected tickets refused: dangerous held 2/2, 0 unauthorised, 0 policy leaks |
| 18 | Redact PII before the model | **DONE** | A | lab w17 |
| 19 | Fine-tune vs RAG vs prompting | **DONE** | A + C | lab w23 (cost model, constraints, break-even) |
| 20 | LoRA on 5K examples | OUT OF SCOPE | — | training work, not application work |
| 21 | Serve an open model at scale | OUT OF SCOPE | — | inference infrastructure, not application work |
| 22 | SSE streaming and disconnects | **DONE** | A | lab w22 (resume, idempotency, cost) |
| 23 | Trace a multi-agent workflow | **DONE** | B | `scout` stage 06; tracing in `triage` stage 05 |
| 24 | Roll back a bad prompt change | PARTIAL | A | new drill: canary + revert decision |
| 25 | Chat for 1M daily users | GAP | C | capacity writeup with arithmetic |

Tally: **17 done, 3 partial, 3 gaps, 2 out of scope.**

Topic 19 stays as a short decision writeup, because choosing between prompting, retrieval
and fine-tuning is an application-side judgment and it comes up in interviews. Topics 20
and 21 are dropped: they are training and serving work, they cannot run in an offline
repository, and they are not what the application-side roles ask for.

---

## 4. The next six, in priority order

Priority is set by hiring weight and by how much the result teaches. Each is a drill
unless stated. The reranker is listed first because it was first in line, not because it is
still the best next move: it has been attempted and rejected for this lab.

### 1. Reranker (topic 05) — DONE, twice measured, not shipped

First as a lab drill, then as `ragkit` stage 09. Both attempts agree, and the second one says
why the first one failed.

The lab attempt (`drills/w16_rerank/`, since removed) reranked 97 paragraphs against 16 queries
and never beat BM25: 0.527 nDCG@5 for the first stage against 0.514 for the best reranked
configuration. The queries and the passages shared little vocabulary, so a term-statistics
stand-in had no signal.

The project attempt used `ragkit`'s corpus, where the queries do use the documents' own words,
so the stand-in had signal — and the result is a rule rather than a win:

| first stage | recall@5 | MRR | MRR after reranking | gain |
| --- | --- | --- | --- | --- |
| dense | 78.3% | 0.541 | 0.668 | **+0.128** |
| lexical | 95.7% | 0.701 | 0.725 | +0.024 |
| hybrid | 95.7% | 0.732 | 0.741 | +0.009, and −2 recall points |

**The gain is the first stage's headroom.** A weak first stage leaves something to repair; a
strong one does not, and the chunks a reranker demotes on a strong stage are the ones fusion got
right. So the decision rule is: look at the first stage's MRR before building a second stage.

**And none of it is significant.** On 23 development questions the dense gain is 7 wins and 3
losses, p = 0.34, and the nine-question held-out split flips its sign (+0.128 dev, −0.019 held
out). The reranker is not in the pipeline. What shipped is the measurement and the rule.

That also explains the lab's null result without excusing it: the lab's first stage was already
the strongest available, so there was nothing for a second stage to fix.

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

**`triage` (9 stages).** Support agent: classify, retrieve policy, draft, escalate.
Covers tools with approval gates, audit trails, trajectory eval, tracing, judge
calibration, and the production loop. This is the repo that answers topics 10, 11, 15,
and 23 in one system, and topic 16 in code: stage 08 calibrates two judges against 27
authored human verdicts — the lenient one is 74.1% raw agreement and κ 0.17, the
calibrated rubric κ 1.00 (fit-to-golds; Shopify's human ceiling was 0.69). Stage 09
replays the stage 07 candidates as twelve days of traffic: the neutral change pages
0/7 days at k = 2 while a too-tight rule pages on noise, the regression is caught the
day it ships, and the failing runs are promoted into the next release's regression set.
It also answers topic 17 with a measured adversarial set: three injected tickets try to
mint authority, invent a capability, and rewrite the policy, and all three are refused
by structure (the gate, the registry, the policy store) — 2/2 dangerous held, 0
unauthorised, 0 injected text in drafts. PII redaction is lab w17, not here.

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
