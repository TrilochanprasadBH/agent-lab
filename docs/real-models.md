# Running against a real model

Only drill 01 supports this. The other fourteen are deterministic worlds: their
ground truth is fixed, and a real model would change the lesson rather than the
exercise. The harness refuses `--provider` for those drills rather than pretending
otherwise.

## 1. Why the drills are simulated by default

Three reasons, in order of importance.

**Determinism.** With a simulated model, a score change always means you changed
something. With a real model at temperature 0, a three-point swing on 96 items is
ordinary noise, and you can spend a week chasing it.

**Speed.** The simulated model responds instantly. A two-second feedback loop is what
makes daily practice possible; a thirty-second one is what makes you stop running it.

**Cost.** A drill run makes 50 to 150 model calls. At real prices, iterating is a
paid activity. The simulated model is free.

The simulated model is not a toy: it fails in the ways real models fail, which is why
the scaffolding you build for it transfers.

## 2. Setup

```sh
export OPENROUTER_API_KEY=sk-or-...
```

The key is read from the environment only. It is never accepted as a command-line
flag, so it does not end up in your shell history or in the process list.

## 3. Start small

Never begin with the full corpus. Five documents is enough to catch a bad key and a
malformed request:

```sh
python3 run.py --drill w01_extraction --provider openrouter --model <model-id> --limit 5
```

Model ids are listed at <https://openrouter.ai/models>. Choose something small and
cheap. Extraction is not a reasoning-heavy task.

Then the full run:

```sh
python3 run.py --drill w01_extraction --provider openrouter --model <model-id>
```

## 4. What changes when the model is real

**The failure distribution changes.** The simulated model truncates, refuses, returns
the wrong party, and produces arithmetic that does not add up. A strong real model
does those things much less often, and fails differently: an extra sentence of
commentary, an inconsistent date format, an occasional invented field on a badly
formatted invoice.

If your code survives the simulator it will usually survive the real model, but not
always in the same places. That is worth seeing once per drill.

**The scores become noisy.** See section 6.

**Costs become real.** The cost line on the scorecard stops being a metaphor.

**Latency becomes the dominant number.** 48 documents at one call each is a minute of
wall clock, not two seconds. Use `--limit` while you are still shaping the solution.

## 5. The response cache

Every real response is cached on disk under `.cache/agentlab/`.

The cache key is the model, the system prompt, the prompt, the temperature and the
maximum token count. Change any of those and the call is made again, which is
correct: a different request is a different call.

```sh
python3 run.py --drill w01_extraction --provider openrouter --model <id>   # pays
python3 run.py --drill w01_extraction --provider openrouter --model <id>   # free
python3 run.py --drill w01_extraction --provider openrouter --model <id> --no-cache
```

Why this matters: an eval loop is run dozens of times while you iterate. At real
prices that habit dies quickly, and a habit that costs money is a habit you stop.

Delete the directory to reclaim space or force a full re-run.

## 6. Determinism, honestly

`temperature=0` does not guarantee identical output. Consequences for practice:

- Compare distributions, not single runs. A three-point difference on 48 documents is
  noise, not progress.
- When a change looks like it helped, rerun with `--no-cache` before believing it.
- Use the simulated provider for the tight iteration loop, and the real one to check
  that your wrapper survives a different failure distribution.

This is the same problem drill 12 is about. If you have not done drill 12 yet, do it
before you trust any real-model comparison.

## 7. Cost control, in order

1. `--limit 5` while shaping the solution.
2. The cache, on by default.
3. `--cap` to set the budget you are willing to spend.
4. `--target` to raise the bar once the cheap version passes.

## 8. Adding another provider

Implement this interface:

```python
class MyModel:
    name = "mine"

    def reset(self) -> None: ...
    def complete(self, prompt: str, system: str | None = None) -> Response: ...

    @property
    def cost_usd(self) -> float: ...
    @property
    def latencies(self) -> list[float]: ...
    @property
    def n_calls(self) -> int: ...

    calls: list[dict]     # one entry per call, for --trace
```

`Response` is defined in `agentlab/model.py`. Register the provider in
`agentlab/providers.py:make_provider` and pass `--provider mine`.

Keep the cache discipline: key on everything that changes the answer, and record a
cache hit as costing zero. Charging yourself for a cached call corrupts the one
number the drill exists to measure.
