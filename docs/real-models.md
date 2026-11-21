# Running the drills against a real model

The lab ships with a simulated model because a free, deterministic, instant model
is what makes daily practice possible. But the same drills run against a real
model, and the day you have a key this is a flag, not a migration.

## Setup

```sh
export OPENROUTER_API_KEY=sk-or-...
```

The key is read from the environment only. It is never a command-line flag, so
it does not end up in your shell history or in `ps`.

## Start cheap

Never begin with the full corpus. Five documents is enough to catch an import
error and a bad key:

```sh
python3 run.py --provider openrouter --model <model-id> --limit 5
```

Model ids live at <https://openrouter.ai/models>. Pick something small and cheap
first; extraction is not a reasoning-heavy task and you will run it dozens of
times.

Then the full run:

```sh
python3 run.py --provider openrouter --model <model-id>
```

## What changes, honestly

**Your wrapper is now tested against a different enemy.** The simulated model
fails in the ways models characteristically fail — truncation, refusals, wrong
party, arithmetic that doesn't add up. A strong real model fails far less, and
mostly differently: occasional markdown, inconsistent date formats, an extra
commentary sentence, the odd hallucinated field on a badly formatted invoice.
If your code survives the simulator it will usually survive the real model, but
not always in the same places. That is worth seeing once per drill.

**Scores become noisy.** See determinism below.

**Costs become real.** The scorecard's cost line stops being a metaphor. Your
retry policy now has a price.

**Latency becomes the dominant number.** 48 documents at one call each is a
minute of wall clock, not two seconds. `--limit` is your friend.

## Cost control ladder

Use these in order:

1. `--limit 5` while you are still getting the shape right.
2. The response cache, on by default. Identical requests are free after the
   first run, so iterating on *scoring* code costs nothing.
3. `--cap` to set the budget you are actually willing to spend, then design
   your retry policy to fit under it.
4. `--target` to raise the bar once the cheap version passes.

The cache is keyed on model, system prompt, prompt, temperature, and
`max_tokens`. Change any of those and you pay again, which is correct: a
different request is a different call.

```sh
python3 run.py --provider openrouter --model <id>     # first run pays
python3 run.py --provider openrouter --model <id>     # second run is free
python3 run.py --provider openrouter --model <id> --no-cache   # force fresh calls
```

Cache lives in `.cache/agentlab/`. Delete it to reclaim disk or force a full
re-payment.

## Determinism

`--temperature 0` is not a promise of identical output, and you should not
pretend otherwise. Consequences for practice:

- Compare *distributions*, not single runs. A 3-point swing between runs on 48
  documents is noise, not progress.
- When a change looks like it helped, rerun with `--no-cache` before you believe
  it. Otherwise you may be scoring the cache.
- The simulated provider is the one that is bit-for-bit deterministic. Use it
  for the tight iteration loop and the real provider to validate.

## Adding another provider

Implement the contract and the whole lab works with it:

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
    calls: list[dict]
```

`Response` lives in `agentlab/model.py`. Register it in
`agentlab/providers.py:make_provider` and pass `--provider mine`.

Keep the cache discipline: key on everything that changes the answer, and record
a cache hit as costing zero. Charging yourself for a cached call corrupts the
one number the drill exists to measure.
