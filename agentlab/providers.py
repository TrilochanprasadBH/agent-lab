"""Model providers behind one interface.

Everything in the lab talks to a provider the same way:

    provider.complete(prompt, system=None) -> Response
    provider.cost_usd, provider.latencies, provider.n_calls, provider.calls
    provider.reset()

That is the whole contract. Swapping the simulated model for a real one is a
flag, not a rewrite.

Two providers ship here:

    SimModel         deterministic, offline, free — the default
    OpenRouterModel  real calls, real money, needs OPENROUTER_API_KEY

Why the cache matters
---------------------
An eval loop is run dozens of times an hour while you iterate. At real prices
that habit dies fast, and a habit that costs money is a habit you stop. So every
real call is cached on disk, keyed by the exact request. Identical requests are
free afterwards; changed prompts and changed temperatures are not cached, which
is correct — those are genuinely different calls.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import time
import urllib.error
import urllib.request

from .model import Response, SimModel

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
CACHE_ROOT = pathlib.Path(os.environ.get("AGENTLAB_CACHE", ".cache/agentlab"))

# Used only when the API does not report a cost. Deliberately conservative.
FALLBACK_PRICE_PER_MTOK = {"in": 1.00, "out": 3.00}


class ProviderError(RuntimeError):
    """A provider could not be built or a call failed unrecoverably."""


def _cache_path(namespace: str, key: str) -> pathlib.Path:
    return CACHE_ROOT / namespace / key[:2] / f"{key}.json"


def _read_cache(namespace: str, key: str) -> dict | None:
    path = _cache_path(namespace, key)
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _write_cache(namespace: str, key: str, payload: dict) -> None:
    path = _cache_path(namespace, key)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        tmp.replace(path)
    except OSError:
        pass  # a cache failure must never fail a drill


class OpenRouterModel:
    """A real model behind the OpenRouter chat-completions endpoint.

    Uses only the standard library, so it works in any environment Python does.
    """

    name = "openrouter"

    def __init__(
        self,
        model_id: str,
        *,
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 900,
        timeout: float = 90.0,
        use_cache: bool = True,
        retries: int = 3,
        app_name: str = "agent-lab",
    ) -> None:
        if not model_id:
            raise ProviderError(
                "OpenRouter needs a model id. Pass --model, for example\n"
                "    --model <model-id-from-openrouter.ai/models>"
            )

        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ProviderError(
                "No OpenRouter key found. Export it in the environment:\n"
                "    export OPENROUTER_API_KEY=sk-or-...\n"
                "Keys are read from the environment, not from flags, so they stay\n"
                "out of your shell history and process list."
            )

        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retries = retries
        self.use_cache = use_cache
        self.app_name = app_name
        self._api_key = key

        self.calls: list[dict[str, object]] = []
        self._cost = 0.0
        self._latencies: list[float] = []
        self.cache_hits = 0

    # -- bookkeeping ------------------------------------------------------

    def reset(self) -> None:
        self.calls.clear()
        self._cost = 0.0
        self._latencies.clear()
        self.cache_hits = 0

    @property
    def cost_usd(self) -> float:
        return self._cost

    @property
    def latencies(self) -> list[float]:
        return list(self._latencies)

    @property
    def n_calls(self) -> int:
        return len(self.calls)

    def cache_key(self, prompt: str, system: str | None) -> str:
        blob = json.dumps(
            {
                "model": self.model_id,
                "system": system or "",
                "prompt": prompt,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            sort_keys=True,
        )
        return hashlib.sha256(blob.encode()).hexdigest()

    # -- the contract -----------------------------------------------------

    def complete(self, prompt: str, system: str | None = None) -> Response:
        key = self.cache_key(prompt, system)
        cached = _read_cache(self.name, key) if self.use_cache else None

        started = time.perf_counter()
        if cached is not None:
            text = cached["text"]
            usage = cached.get("usage") or {}
            finish = cached.get("finish_reason", "stop")
            self.cache_hits += 1
            cost = 0.0
        else:
            body = self._request(prompt, system)
            choices = body.get("choices") or []
            if not choices:
                raise ProviderError(f"no choices in response: {body!r}"[:400])
            message = choices[0].get("message") or {}
            text = message.get("content") or ""
            if not isinstance(text, str):
                text = str(text)
            finish = choices[0].get("finish_reason", "stop")
            usage = body.get("usage") or {}
            cost = self._cost_of(usage)
            if self.use_cache:
                _write_cache(
                    self.name,
                    key,
                    {"text": text, "usage": usage, "finish_reason": finish},
                )

        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        tokens_in = int(usage.get("prompt_tokens") or max(1, len(prompt) // 4))
        tokens_out = int(usage.get("completion_tokens") or max(1, len(text) // 4))

        self._cost += cost
        self._latencies.append(elapsed_ms)
        self.calls.append(
            {
                "model": self.model_id,
                "cached": cached is not None,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(cost, 8),
                "latency_ms": elapsed_ms,
                "finish_reason": finish,
                "prompt_tail": prompt[-160:],
                "output": text,
            }
        )

        return Response(
            text=text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=elapsed_ms,
            cost_usd=cost,
            finish_reason=finish,
            cached=cached is not None,
        )

    # -- internals --------------------------------------------------------

    def _cost_of(self, usage: dict) -> float:
        reported = usage.get("cost")
        if isinstance(reported, (int, float)):
            return float(reported)
        tokens_in = int(usage.get("prompt_tokens") or 0)
        tokens_out = int(usage.get("completion_tokens") or 0)
        return (
            tokens_in * FALLBACK_PRICE_PER_MTOK["in"]
            + tokens_out * FALLBACK_PRICE_PER_MTOK["out"]
        ) / 1_000_000

    def _payload(self, prompt: str, system: str | None) -> dict:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return {
            "model": self.model_id,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "usage": {"include": True},
        }

    def _request(self, prompt: str, system: str | None) -> dict:
        payload = json.dumps(self._payload(prompt, system)).encode()
        last: Exception | None = None

        for attempt in range(self.retries):
            request = urllib.request.Request(
                OPENROUTER_URL,
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": f"https://localhost/{self.app_name}",
                    "X-Title": self.app_name,
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode())
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode(errors="replace")[:300]
                last = ProviderError(f"HTTP {exc.code}: {detail}")
                if exc.code not in (408, 409, 429, 500, 502, 503, 504):
                    raise last from None
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last = ProviderError(f"{type(exc).__name__}: {exc}")

            if attempt < self.retries - 1:
                time.sleep(0.8 * (2**attempt))

        raise last or ProviderError("request failed")


def make_provider(
    kind: str | None = "sim",
    *,
    corpus_texts: list[str] | None = None,
    seed: int = 7,
    model_id: str | None = None,
    **kwargs,
):
    """Build a provider by name."""
    normalised = (kind or "sim").strip().lower()

    if normalised in ("sim", "simulated", "fake", "local"):
        return SimModel(list(corpus_texts or []), seed=seed)

    if normalised in ("openrouter", "real"):
        if not model_id:
            raise ProviderError(
                "OpenRouter needs a model id. Use --model <id>, from\n"
                "    https://openrouter.ai/models"
            )
        return OpenRouterModel(model_id, **kwargs)

    raise ProviderError(f"unknown provider {kind!r}; try 'sim' or 'openrouter'")
