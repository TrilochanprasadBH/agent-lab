# w20 — Debug the wrong answer

| | |
| --- | --- |
| **Goal** | From a failing question and its trace, name the first stage where the evidence disappeared, and the repair that follows. |
| **Outcome** | 100% of 42 cases diagnosed on stage and repair, from a baseline of 14.3%. |
| **Target** | joint accuracy ≥ 90% (stage and repair both right) |
| **Time** | 60 to 90 minutes |

## 1. Why this drill exists

"The model gave a wrong answer" is a description of the symptom, not of the bug. In a RAG system
there are seven places the evidence can stop, and only one of them is the model. Diagnosing which
one is the difference between a fix that works and a week of prompt edits that change nothing.

The drill is built so that the symptom cannot help you. All 42 cases have a wrong answer. The
retrieval score is at or above 0.85 in all 42, including the six where retrieval is the fault. In
30 of 42 the answer is fluent and states a value that really is in the corpus — just the wrong
one — which is exactly what a hallucination looks like from the outside.

The baseline, which blames the model, scores 14.3%: it is right exactly six times, in the six
cases where the model is the problem.

## 2. What you are given

- `data.py`: 42 cases over six documents and 36 unique facts.
- `data.Case`: the question, the query the retriever actually ran (`rewritten`), the full
  `ranking` with scores, the `k` cut, the chunks that reached the prompt, the token count and
  the packer's policy, and the answer.
- `data.Case.index`: every chunk, with the fact it states (`value`) and whether it is
  `superseded`. `data.Case.corpus`: the source documents, so you can tell a missing document from
  a missing chunk.
- `data.Case.trace()`: the same thing rendered as text, which is what the failure list shows.
- `task.py`: blame the model.
- `sweep.py`: four strategies and the symptom breakdown.
- `check_labels.py`: verifies that every case really contains the fault it claims.

The cases are authored, because the drill needs a trace whose fault is known exactly. Every gold
value is unique across the corpus and `check_labels.py` proves it — with 36 facts over six
documents, a duplicate value would make "the gold is in the index" ambiguous and every downstream
check unreliable.

## 3. How to run it

```sh
python3 drills/w20_debug/check_labels.py
python3 drills/w20_debug/sweep.py
python3 run.py --drill w20_debug
python3 run.py --drill w20_debug --task solutions/w20_reference.py
```

## 4. Background: a pipeline is a sequence of filters

Each stage can only lose evidence the stage before it passed on. That gives one algorithm:

> **Check the stages in pipeline order and stop at the first one where the evidence is gone.**

| stage | the first "no" | repair | what happens if you repair the wrong thing |
| --- | --- | --- | --- |
| ingestion | the value is in no chunk at all | `reingest` | you add prompt instructions; nothing improves |
| chunking | the text survives, but no single chunk holds it | `rechunk` | you raise `k`; a chunk that does not exist cannot rank |
| query | the rewrite dropped the term that disambiguates | `rewrite` | you add BM25 and rank the wrong question better |
| retrieval | the chunk exists and the query was fine; it is below the cut | `raise_k` or `hybrid` | you blame the prompt |
| packing | retrieved, then left out of the prompt | `repack` | you blame the model |
| generation | in the prompt, not in the answer | `ground` | you swap models for a prompt bug |
| stale | an older superseded chunk outvoted the current one | `supersede` | grounding makes it cite the old value more confidently |

Two pairs need care, because both members produce the same symptom.

**`query` versus `retrieval`.** Both mean "the chunk was not retrieved". The difference is whether
the rewritten query still contains the term that makes the question specific. If it does, the
retriever failed on a fair question. If it does not, the retriever was asked the wrong question,
and better retrieval will answer it better.

**`stale` versus `generation`.** Both mean "the value never reached the answer". Stale means the
prompt carried a superseded value that outvoted the current one. That is a different repair:
telling the model to ground its answer makes it ground the *wrong* chunk more confidently.

**Retrieval has two repairs, and the rank decides.** A chunk three places below the cut is a `k`
problem; raising `k` is one line and costs one more chunk of context. A chunk at rank 18 is a
matching problem; raising `k` to 18 buys latency and puts five more distractors in the prompt.
The drill's retrieval cases sit at ranks 6 to 8 and 15 and above, so the choice is never
ambiguous.

### The measurement

| strategy | joint | stage | fix | what it misses |
| --- | --- | --- | --- | --- |
| blame the model | 14.3% | 14.3% | 14.3% | everything that is not the last stage |
| score heuristic | 21.4% | 21.4% | 21.4% | confidence is not a diagnosis |
| cheap checks, natural order | 35.7% | 42.9% | 35.7% | chunking, query, packing, stale |
| first-failure ladder | **100%** | 100% | 100% | nothing |

The third row is the important one. `cheap checks` knows all seven stages; it differs from the
ladder only in the order it asks the questions. It checks the index, then the ranking, then the
answer — which sounds sensible and costs 64 points. **Knowing more is not what fixes this; asking
in the order the pipeline runs is.**

And what the trace looks like before you ask anything:

| symptom | cases |
| --- | --- |
| the answer admits it could not find the document | 15 |
| the answer states a real value from the wrong chunk | 15 |
| the answer states an older value from a superseded chunk | 6 |
| the answer invents a number that appears nowhere | 6 |
| top retrieval score at or above 0.85 | 42 |

## 5. The task, step by step

1. Read one trace and write down what you think is wrong. Then run the baseline and note that you
   just did what it does.
2. Implement the first check only: is the gold in the index at all? Count how many cases that
   explains.
3. Add the chunk check. The test is that the value survives string concatenation but no single
   chunk contains it — the text is there and unusable.
4. Add retrieval, then split it: did the rewrite keep the term? Then look at the rank.
5. Add packing, then the final split between a stale chunk and a model that ignored good
   evidence.
6. Run `check_labels.py`. If you misread a signature, it fails on the case, not on a summary.

Return `{"stage": ..., "fix": ...}`.

## 6. How you are scored

| metric | weight |
| --- | --- |
| joint diagnosis | the accuracy line, target 90% |
| stage right | reported separately: right place, wrong explanation |
| repair right | reported separately: would the fix have worked |
| per stage | one bar per stage, six cases each |
| cost | zero. This drill calls no model |

The joint number is the one that matters. A stage without the repair is a diagnosis you cannot
act on, and a repair without the stage is a guess that happened to match the vocabulary.

The target is 90%, not 85%, because the taxonomy is exact: a learner who handles six of seven
stages scores 85.7% and has one systematic hole. The per-stage bars name it.

## 7. Done when

- [ ] `python3 run.py --drill w20_debug --task solutions/w20_reference.py` reports TARGET MET
- [ ] you can state the seven stages in pipeline order and the one check each one corresponds to
- [ ] you can explain why `cheap checks` loses 64 points without knowing less
- [ ] you can name the two pairs that share a symptom and say what separates them
- [ ] you can say why a rank of 7 and a rank of 18 get different repairs
- [ ] `check_labels.py` passes, and you can say what it would catch if you edited the corpus

## 8. Carry forward

The method generalises past RAG. Any pipeline is a sequence of filters, and the cheapest debugging
move in existence is to check the stages in order and stop at the first one that lost the thing
you needed. The same ladder diagnoses a failed agent run (did the tool get called, did it return,
did the result reach the next prompt) and a failed eval (is the answer wrong, or is the label
wrong).

What this drill does not model: several faults at once (every case has exactly one), a fault in
the evaluation set rather than the pipeline, retrieval over more than six documents, and the cost
of a wrong diagnosis in wall-clock terms. The last one is worth stating because the numbers hide
it: a team that misdiagnoses `packing` as `generation` does not get a wrong score, it gets a
quarter of prompt engineering and the same failure rate, and then concludes that the model is not
good enough. That is the expensive version of the 14.3% baseline.

The other limit is that the ranking here is a fixture shaped by the fault rather than the output
of a real retriever. That is deliberate — the drill is about reading a trace — but it means the
drill cannot tell you whether your retriever is any good. `ragkit` stage 04 does that, with a
measured nDCG and a negative control.
