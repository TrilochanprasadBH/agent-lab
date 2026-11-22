# Glossary

Every technical term used in this repository, defined once. If a word in a spec is
not here, that is a bug in the documentation.

Terms are grouped. Read the first group before drill 01.

---

## 1. The model

**Model (language model)**
A function that takes text and returns text. Nothing more. It does not remember
previous calls, it does not run code, and it cannot see your files.

**Prompt**
The text you send to the model.

**Completion**
The text the model returns.

**Token**
The unit models use to measure text. Roughly three quarters of an English word.
Models have a maximum number of tokens they can process, and they charge per token.

**Context window**
The maximum number of tokens a model can consider in one call. Everything must fit:
your instructions, the documents, the conversation, and the answer.

**Temperature**
A setting that controls randomness. At 0 the model is nearly deterministic, which
is why eval runs usually set it to 0. It is not perfectly deterministic: identical
input can still produce different output.

**Simulated model**
A stand-in for a real model that is written in Python and runs locally. In this
repository it is deterministic, free, and designed to fail in the ways real models
fail. Every drill uses one except drill 01, which can also use a real model.

**Deterministic**
Same input, same output, every time. Simulated models here are deterministic. Real
ones are not.

---

## 2. Retrieval

**Document**
A piece of text stored in a collection. In drill 02 the documents are runbooks.

**Term**
A word, after lowercasing and removing punctuation and stop words.

**Stop word**
A very common word that carries little meaning: "the", "and", "of". Removing them
makes matching cleaner.

**Stemming**
Reducing a word to a common form so variants match. "evicting", "evicted" and
"evicts" all become "evict". Crude stemming is enough for retrieval.

**Inverted index**
A map from term to the list of documents containing it. It is how you find
candidates without reading every document.

**IDF (inverse document frequency)**
A weight for a term based on how rare it is. A term in two documents is informative;
a term in thirty is not. Formally `log((N + 1) / (df + 1)) + 1`, where `N` is the
number of documents and `df` is how many contain the term.

**Ranking**
Ordering documents by how well they match a query. Retrieval means returning the
best few, not all of them.

**recall@k**
Of all the questions where a correct document exists, the fraction where it appears
in the top `k` results. Recall measures whether the right document was found at all.

**first-hit (precision at 1)**
The fraction of questions where the correct document was ranked first. Ranking
quality matters because the model reads the top of the list first.

---

## 3. Context

**Budget**
A hard limit on how many tokens you may spend. In drill 03 the budget is 120 words.

**Packing**
Choosing which documents to put in the context window and in what order, so that
the needed evidence fits inside the budget.

**Coverage**
The fraction of questions whose required evidence is present in the packed context.

**Truncation**
Cutting text short to fit a budget. Where you cut matters: cutting mid-sentence
often removes the clause that answered the question.

---

## 4. Tools and agents

**Tool**
A function the model is allowed to ask you to run, described by a name and a
parameter schema.

**Tool call**
A structured request from the model, for example `get_order(order_id="o8712")`.
It arrives as text. You must parse it and validate it before anything runs.

**Schema**
A description of what a valid call looks like: which parameters exist, their types,
which are required, and which values are allowed.

**Validation**
Checking a call against the schema before running it. Validation must happen before
execution, not after.

**Dangerous action**
A tool call that changes state or sends data outside the system: a refund, a
deletion, an email. These require a human decision, not a model decision.

**Confirmation**
An explicit human approval for a dangerous action. A model writing `confirm: true`
is the model's opinion, not human consent.

**Observation**
The result of a tool call, fed back into the next prompt. Without observations the
model cannot know what happened.

**Agent**
A loop: call the model, run any tool calls, add the results to the prompt, repeat
until the model answers or the budget runs out.

**Agent loop**
The implementation of that repetition. It has four responsibilities: build the
prompt, execute calls, detect when to stop successfully, and detect when to stop
unsuccessfully.

**Step budget**
A maximum number of iterations. Without one, a confused agent runs forever.

**Grounded**
An answer is grounded when it is supported by text that was actually provided. An
ungrounded answer is a guess that reads like a fact.

**Trajectory**
The full sequence of steps in an agent run: prompts, tool calls, observations, and
the final answer. Evaluating a trajectory means scoring the process, not only the
answer.

---

## 5. Evaluation

**Eval (evaluation)**
A repeatable test that scores a system's output. An eval has three parts: a set of
items, a way to score each item, and a threshold for passing.

**Eval set (test set)**
The collection of items used to measure quality. It is a sample, so what it covers
determines what it can detect.

**Ground truth**
The known-correct answer for an item. Required for automatic scoring.

**Baseline**
The starting implementation. A drill's baseline must fail its target, otherwise the
drill teaches nothing.

**Metric**
The number an eval produces. It must be defined precisely enough that two people
computing it get the same value.

**Accuracy**
Here, the fraction of items answered correctly. Not a general measure of quality;
it is whatever the drill defines.

**Normalisation**
Converting output into a standard form before comparing. `"1.350,00 EUR"` and
`1350.00` are the same amount of money and should score as equal.

**Judge (model as judge)**
Using a model to score output that cannot be checked against an exact answer, such
as tone or helpfulness.

**Position bias**
The tendency of a judge to prefer whichever option appears first. It is systematic,
so it can be measured and corrected by swapping the order.

**Noise**
Random error. Unlike bias it has no direction, so it cannot be corrected by
swapping; it can only be outvoted by taking more samples.

**Sampling**
Calling the model more than once and combining the answers. Only useful if the calls
are independent, which requires the prompt to differ between calls.

**Overfitting (of an eval)**
Building a grader that scores well on the data you looked at and badly on data you
did not. Detectable only with a held-out set.

**Held-out (test) set**
Data whose labels you do not see during development, used to measure whether your
method generalises.

**Spurious correlation**
A pattern that exists in one sample by accident. "All good replies start with
Thanks" is true of one writing team and false of the next.

**Precision and recall (of a classifier)**
Precision is the fraction of items you flagged that were correct. Recall is the
fraction of correct items you flagged. A grader can be high in one and low in the
other.

---

## 6. Statistics

**Paired comparison**
Comparing two systems on the same items. Each item gives a pair of results, which
removes item difficulty from the comparison and makes detection far more sensitive.

**Discordant pair**
A pair where the two systems disagree: one passed, the other failed. Only discordant
pairs carry information about which system is better.

**Null hypothesis**
The assumption that there is no real difference and any observed difference is
chance. Statistical tests measure how surprising the data would be under this
assumption.

**p-value**
The probability of seeing a difference at least this large if the null hypothesis
were true. Small values mean the data is unlikely under "no difference".

**Significance level**
The p-value below which you reject the null hypothesis. 0.05 is the usual default.

**McNemar's test**
The test for paired pass/fail data. Count the two kinds of discordant pairs and
check whether the split is consistent with a coin flip.

**Effect size**
How large the difference is, independent of whether it is statistically detectable.
A tiny difference can be real and still not worth shipping.

**Power**
The probability that a test detects a real effect of a given size. Low power means
you will miss real improvements and should collect more items.

**Confidence interval**
A range of plausible values for the true effect. A difference with a wide interval
is uncertain regardless of its point estimate.

---

## 7. Release and reliability

**Regression**
A change that makes something worse that used to work.

**Slice (segment, cohort)**
A subset of the eval items sharing a property: a language, a customer tier, a
document type.

**Aggregate**
The single number computed across all items. It is a summary, and summaries can hide
slices that moved the other way.

**Simpson's paradox**
When every relevant slice improves or stays flat but the aggregate moves the
opposite way, usually because the mix of items changed. The reverse also happens and
is the dangerous case: the aggregate improves while one slice gets worse.

**Gate**
A rule that decides whether a change may ship, based on eval results.

**False ship**
Shipping a change that is actually worse. It reaches users.

**False block**
Blocking a change that was actually fine. It costs time.

**Prompt injection**
An attack where text the system reads contains instructions, and the model follows
them because it cannot distinguish data from instructions.

**Trust boundary**
The line between data you control and data you do not. Everything retrieved from
outside is untrusted.

**Sanitisation**
Removing or neutralising instruction-like content from untrusted text before it
reaches the model.

**Exfiltration**
Sending data out of the system to an unauthorised destination. Usually requires an
outbound tool call, which is why outbound calls must be gated.

**Guardrail**
A rule enforced in code that constrains what the system may do or output,
independent of what the model says.

---

## 8. The harness

**Harness**
The code that runs a drill and produces a scorecard. Fixed and shared, so results
from different drills mean the same thing.

**Provider**
The object that supplies model responses. In this repository: simulated, scripted,
or OpenRouter.

**Scripted model**
A provider that returns pre-written responses. Used for deterministic worlds such as
tool drills, where the lesson is what your code does with the response.

**Scorecard**
The printed summary: the main metric, cost, crashes, per-metric breakdown, failure
modes, and a pass or fail verdict.

**Reference solution**
A known-working implementation of a drill, in `solutions/`. It proves the target is
achievable. Read it after trying, not before.
