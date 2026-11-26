# w21 — First-token latency is a queueing problem

| | |
| --- | --- |
| **Goal** | Serve 2,400 requests at 40 per second without breaking quality, p95 time-to-first-token, or cost. |
| **Outcome** | 95.8% quality at p95 524ms and $0.00049 per request, from a baseline whose p95 is 8 minutes. |
| **Target** | quality ≥ 92%, p95 TTFT ≤ 900ms, cost ≤ $0.0008 per request |
| **Time** | 60 to 90 minutes |

## 1. Why this drill exists

Time-to-first-token is the number a user feels. It is not a property of the model; it is a
property of the queue in front of it. A fast model behind a saturated queue is slow, a slow model
with enough batching is fast enough, and the difference between the two is arithmetic rather than
intuition.

The drill gives you one lever per gate and makes each lever able to break another gate:

- **quality** needs the strong model, and the strong model costs 2.8× the compute per token
- **latency** needs batching, because 40 requests per second do not fit through one unbatched pass
- **cost** needs batching too, because a batch of eight costs one pass, not eight

The starting configuration — best model, no batching, full prompt — has the best quality of any
policy in the table and a p95 of **480 seconds**. It is not a slow system; it is a system whose
queue never recovers. At 40 rps the four slots can serve 7.8 requests per second one at a time,
so every second the backlog grows by 32 requests, and the 95th percentile is the backlog rather
than the request.

## 2. What you are given

- `data.py`: the workload, the machine, and the simulation.
- `data.Request`: arrival time, prompt tokens, output tokens, whether the upstream classifier
  called it hard, and the token offset where the evidence sits. **The offset is not visible to
  your policy** — that is what makes truncation a gamble.
- `data.simulate(requests, decisions, batch_wait_ms)`: returns one `Outcome` per request with
  its TTFT, batch size, cost, and whether it was answered correctly.
- `data.SLOTS = 4`, `BATCH_MAX = 8`: four CUDA streams, at most eight requests in a batch.
- `task.py`: the best model, no batching, the whole prompt.
- `sweep.py`: seven policies and a sweep of the batch window.
- `check_sim.py`: verifies the world and the capacity arithmetic.

The request model is in the module docstring: prefill is linear in prompt tokens, decode is
linear in output tokens and sequential, a batch costs the longest prefill and the longest decode
in it, and that cost is split across the batch.

## 3. How to run it

```sh
python3 drills/w21_ttft/check_sim.py
python3 drills/w21_ttft/sweep.py
python3 run.py --drill w21_ttft
python3 run.py --drill w21_ttft --task solutions/w21_reference.py
```

## 4. Background: three gates, and the knob that moves each one

| policy | quality | p50 | p95 | $/req | batch | fails |
| --- | --- | --- | --- | --- | --- | --- |
| strong, no batch | 97.7% | 252 375ms | 479 892ms | $0.003954 | 1.0 | latency, cost |
| strong, batch | 97.7% | 22 459ms | 42 492ms | $0.000733 | 8.0 | latency |
| fast, batch | 79.1% | 162ms | 264ms | $0.000258 | 8.0 | quality |
| route, no batch | 95.8% | 42 938ms | 91 572ms | $0.002160 | 1.0 | latency, cost |
| route, batch, 200ms | 95.8% | 206ms | 7 202ms | $0.000709 | 5.7 | latency |
| **route, batch, 400ms** | **95.8%** | **228ms** | **524ms** | **$0.000490** | **7.4** | **nothing** |
| route, batch, truncate 700 | 88.1% | 209ms | 489ms | $0.000455 | 7.4 | quality |

Each row fails for a different reason, and three of them fail exactly one gate.

**The strong model cannot serve this load at all.** Four slots, an average strong batch of
941ms, so 4.25 batches per second. At eight per batch that is 34 rps against 40 arriving. The p95
is 42 seconds because the queue grows for the entire minute — the model is not slow, it is
oversubscribed.

**The fast model has 46 points of headroom on latency and none on quality.** On the 30% of
requests the classifier calls hard it is right 42% of the time. Routing those to the strong model
is the whole difference between 79.1% and 95.8%.

**Routing without batching does not help**, because the bottleneck is passes per second, not the
model. Both unbatched policies fail latency and cost together.

**Truncation is the trap.** Cutting every prompt to 700 tokens takes 35ms off p95 and 7.7 points
off quality, because the evidence sits at an offset the server never sees. It is the one knob
here that reads as a latency fix and is a quality loss.

### The batch window has an optimum, and you can predict where it is

| window | quality | p50 | p95 | $/req | batch |
| --- | --- | --- | --- | --- | --- |
| 50ms | 95.8% | 11 925ms | 54 185ms | $0.001435 | 2.1 |
| 100ms | 95.8% | 151ms | 32 468ms | $0.001059 | 3.4 |
| 200ms | 95.8% | 206ms | 7 202ms | $0.000709 | 5.7 |
| 300ms | 95.8% | 224ms | **477ms** | $0.000548 | 7.0 |
| 400ms | 95.8% | 228ms | 524ms | $0.000490 | 7.4 |
| 600ms | 95.8% | 230ms | 654ms | $0.000427 | 7.8 |
| 1200ms | 95.8% | 233ms | 749ms | $0.000404 | 8.0 |

The p95 falls by two orders of magnitude and then rises. The minimum is where the batch just
fills before the queue builds, and the position is computable:

```
strong tier receives      30% x 40 rps              = 11.9 rps
one strong batch costs    0.28 x 700 + 10 x 75      = 941ms
four slots serve          4 / 0.941s                = 4.25 batches/s
batch needed              11.9 / 4.25               = 2.8 requests
window needed             2.8 x (1000 / 11.9)       = 235ms
```

`check_sim.py` prints that arithmetic and asserts that the measured cliff falls between 200ms and
300ms. Below it, the strong tier's queue grows for the whole minute; above it, every request pays
the wait for no extra throughput.

### What the cost number really is

At full batches the cost should be `0.941s x $0.0042 / 8 = $0.000494` for a strong request and
`$0.000174` for a fast one, so routing should cost about `$0.000270`. The measured cost is
`$0.000490`, 1.8× that, for two reasons: batches average 7.4 rather than 8, and **a batch costs
its longest member**. Mixing a 200-token request with a 1200-token one means the short one pays
for the long one's prefill. Batching is not free sharing; it is a queue that bills you at the
maximum.

## 5. The task, step by step

1. Run the baseline. Note the quality is the best in the table and the p95 is eight minutes.
2. Compute the capacity by hand: slots, average service time, requests per second. Decide whether
   the fault is the model, the batch size, or the arrival rate.
3. Turn on batching and re-run. The p95 will still fail if you leave the window at 200ms — find
   out why, and predict the window where it stops failing before you try it.
4. Route the hard requests to the strong model. Check quality and cost together: one moves up,
   the other moves up too.
5. Try truncation. Watch the p95 barely move and the quality gate break.
6. Run `check_sim.py` and compare its predicted window with the one you measured.

Return a decision per request: `tier`, `batch`, `batch_wait_ms`, `max_prompt_tokens`.

## 6. How you are scored

| metric | weight |
| --- | --- |
| answer quality | the accuracy line, target 92%, gated |
| p95 TTFT | gate: above 900ms the run scores zero |
| cost per request | gate: above $0.0008 the run scores zero |
| per-tier quality | reported: easy and hard requests separately |
| truncated | reported: how much evidence you cut to buy latency |

The two gates are why `accuracy` reads 0.0% for a policy with 97.7% quality. The card shows the
quality bar next to the score so the zero is legible: the answers were good and the service was
not.

## 7. Done when

- [ ] `python3 run.py --drill w21_ttft --task solutions/w21_reference.py` reports TARGET MET
- [ ] you can compute the unbatched capacity of this machine without running anything
- [ ] you can explain why the strong model fails the latency gate even at full batches
- [ ] you can predict the batch window's cliff from the strong tier's arrival rate, and say what
      the measured value was
- [ ] you can say why truncating to 700 tokens is a bad trade here, in two numbers
- [ ] `check_sim.py` passes

## 8. Carry forward

The lesson generalises to every latency budget: **find the bottleneck in units of work per
second, not in milliseconds per request.** Once the machine's capacity is below the arrival rate,
no amount of tuning at the request level helps, and the p95 becomes a measure of how long the
queue has been growing rather than of how slow anything is.

What this does not model matters if you take it to production:

- **Prefill is charged at the batch maximum**, not the sum. Real chunked prefill pays closer to
  the sum, so long prompts hurt batches more than they do here.
- **KV-cache memory does not limit the batch.** In reality a batch of eight 1200-token prompts
  may not fit, and the batch size becomes a function of sequence length.
- **There is no admission control.** A real service sheds load with a 429 when the queue passes a
  threshold; here requests wait for eight minutes, which is a modelling choice that makes the
  failure visible rather than polite.
- **TTFT is the first decode step**, with no network hop, no tokeniser, and no streaming
  protocol. Topic 22 is the drill where the stream itself can drop.

The eval question underneath is the one `w12` teaches: a p95 computed over 2,400 requests has a
range, and a change that moves it by 40ms may not be a change at all. This drill reports the
number; deciding whether it moved is a different drill.
