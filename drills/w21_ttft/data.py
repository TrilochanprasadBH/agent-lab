"""A serving simulation: 240 requests, one GPU, and three constraints that cannot all be met.

The workload is fixed and generated from a seed. Each request has an arrival time, a prompt, an
output length, a difficulty flag from an upstream classifier, and the token offset where the
evidence sits in the prompt. The evidence offset is the one thing the server cannot see, which is
what makes truncation a gamble rather than an optimisation.

The machine is simple on purpose:

    prefill    prompt_tokens x prefill rate for the tier
    decode     output_tokens x decode rate for the tier, sequential
    batching   up to 8 requests share one pass; the pass costs the longest prefill and the
               longest decode in the batch, and that cost is split across the batch
    queue      one server, first in first out

That is enough to produce the trade-off every team meets:

- **The strong model alone blows the cost cap.** Two and a half times the compute per token, and
  decode is the expensive half.
- **The fast model alone blows the quality target.** It is accurate on 97% of ordinary requests
  and 42% of the hard ones, and 30% of traffic is hard.
- **No batching blows the latency budget.** 240 requests arrive in 60 seconds; unbatched, the GPU
  needs about twice the wall clock to serve them, so the queue grows without bound.
- **Truncating the prompt is a gamble.** It cuts prefill, but the evidence sits at an offset the
  server never sees. Cut too much and 8% of answers lose their evidence.

The only configuration that clears all three routes the hard requests to the strong model, sends
the rest to the fast one, and batches everything. `sweep.py` measures the alternatives, including
the two that look sensible and fail on exactly one gate.

The cost model is GPU time: a batch of eight costs one pass, not eight, so the per-request cost
falls as the batch fills. That is why batching is not optional here — it is the only lever that
improves latency and cost together.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

N_REQUESTS = 2400
WINDOW_MS = 60_000.0

# The serving box runs four batch slots. A slot is a CUDA stream: it processes one batch at a
# time, and the next batch starts when a slot frees up.
SLOTS = 4
BATCH_MAX = 8

# Milliseconds of GPU time per token, per tier.
PREFILL_MS = {"fast": 0.10, "strong": 0.28}
DECODE_MS = {"fast": 3.5, "strong": 10.0}

# Dollars per GPU-second, scaled so an unbatched strong request costs about half a cent.
GPU_RATE = 0.0042

GOLD_TOKENS = 60

# The chance a request is answered correctly, before truncation. `u` is a fixed draw per request,
# so the same request succeeds or fails identically under every policy: the comparison is paired.
ACCURACY = {
    ("fast", False): 0.97,
    ("fast", True): 0.42,
    ("strong", False): 0.99,
    ("strong", True): 0.94,
}

TTFT_BUDGET_MS = 900.0
COST_CAP_USD = 0.0008
QUALITY_TARGET = 0.92


def _unit(*parts: object) -> float:
    digest = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(digest[:13], 16) / float(16**13)


@dataclass(frozen=True)
class Request:
    id: str
    arrival_ms: float
    prompt_tokens: int
    output_tokens: int
    hard: bool
    gold_at: int
    difficulty: float
    raw: str = ""


@dataclass
class Outcome:
    request: Request
    tier: str
    batch_size: int
    ttft_ms: float
    cost_usd: float
    correct: bool
    evidence_kept: bool
    error: str | None = None


def build(seed: int = 2027) -> list[Request]:
    requests = []
    per_request = WINDOW_MS / N_REQUESTS
    for index in range(N_REQUESTS):
        prompt = 200 + int(_unit(seed, index, "prompt") * 1000)
        output = 30 + int(_unit(seed, index, "output") * 90)
        hard = _unit(seed, index, "hard") < 0.30
        # The evidence always fits inside the prompt, otherwise every policy would lose it.
        gold_at = int((prompt - GOLD_TOKENS) * (0.15 + 0.70 * _unit(seed, index, "gold")))
        # 40 requests per second, with enough jitter that batches are not all the same size.
        arrival = index * per_request + (_unit(seed, index, "arrival") - 0.5) * per_request
        requests.append(
            Request(
                id=f"r{index + 1:04d}",
                arrival_ms=round(max(0.0, arrival), 1),
                prompt_tokens=prompt,
                output_tokens=output,
                hard=hard,
                gold_at=gold_at,
                difficulty=_unit(seed, index, "u"),
                raw=f"{prompt:>5} prompt, {output:>3} output, "
                f"{'hard' if hard else 'easy'}, evidence at {gold_at}",
            )
        )
    return requests


def _prompt_used(request: Request, decisions: dict[str, dict]) -> int:
    """The prompt the server actually prefills: the request's, unless the policy truncates it."""
    cap = decisions[request.id].get("max_prompt_tokens", request.prompt_tokens)
    return min(request.prompt_tokens, cap)


def _service_ms(
    tier: str, batch: list[Request], decisions: dict[str, dict]
) -> tuple[float, float]:
    """(service time, prefill) for one batched pass over these requests."""
    prefill = max(PREFILL_MS[tier] * _prompt_used(request, decisions) for request in batch)
    decode = DECODE_MS[tier] * max(request.output_tokens for request in batch)
    return prefill + decode, prefill


def simulate(
    requests: list[Request], decisions: dict[str, dict], batch_wait_ms: float = 200.0
) -> list[Outcome]:
    """Serve the workload in arrival order and return one outcome per request.

    Each tier is its own deployment: its own queue and its own batch slots. A batch cannot mix
    models, which is why the router's choice also decides which queue a request waits in.
    """
    outcomes: list[Outcome] = []
    pending: dict[str, list[Request]] = {tier: [] for tier in PREFILL_MS}
    slots: dict[str, list[float]] = {tier: [0.0] * SLOTS for tier in PREFILL_MS}

    def flush(tier: str, batch: list[Request]) -> None:
        if not batch:
            return
        service, prefill = _service_ms(tier, batch, decisions)
        slot = min(range(SLOTS), key=lambda index: slots[tier][index])
        start = max(slots[tier][slot], batch[-1].arrival_ms)
        slots[tier][slot] = start + service
        cost = (service / 1000.0) * GPU_RATE / len(batch)

        for request in batch:
            evidence_kept = _prompt_used(request, decisions) >= request.gold_at + GOLD_TOKENS
            correct = request.difficulty < ACCURACY[(tier, request.hard)] and evidence_kept
            outcomes.append(
                Outcome(
                    request=request,
                    tier=tier,
                    batch_size=len(batch),
                    ttft_ms=(start - request.arrival_ms)
                    + PREFILL_MS[tier] * _prompt_used(request, decisions)
                    + DECODE_MS[tier],
                    cost_usd=cost,
                    correct=correct,
                    evidence_kept=evidence_kept,
                )
            )

    for request in sorted(requests, key=lambda item: item.arrival_ms):
        decision = decisions.get(request.id, {})
        tier = decision.get("tier")
        if tier not in PREFILL_MS:
            outcomes.append(
                Outcome(
                    request=request,
                    tier=str(tier),
                    batch_size=1,
                    ttft_ms=TTFT_BUDGET_MS + 1.0,
                    cost_usd=0.0,
                    correct=False,
                    evidence_kept=False,
                    error=f"unknown tier {tier!r}; expected one of {sorted(PREFILL_MS)}",
                )
            )
            continue

        if decision.get("batch"):
            queue = pending[tier]
            if queue and request.arrival_ms - queue[0].arrival_ms >= batch_wait_ms:
                flush(tier, queue)
                queue = []
                pending[tier] = queue
            queue.append(request)
            if len(queue) >= BATCH_MAX:
                flush(tier, queue)
                pending[tier] = []
        else:
            flush(tier, pending[tier])
            pending[tier] = []
            flush(tier, [request])

    for tier, queue in pending.items():
        flush(tier, queue)
    return outcomes


def model():
    """No external model: the world is the simulated server."""

    class World:
        name = "serving-simulation"
        cost_usd = 0.0
        latencies: list[float] = []
        n_calls = 0
        calls: list[dict] = []

        def reset(self) -> None:
            self.latencies = []
            self.calls = []

    return World()
