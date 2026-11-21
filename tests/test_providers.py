"""Provider tests.

No network. The HTTP layer is replaced with a canned response, which is exactly
what the cache is there to make possible — the interesting behaviour is
accounting and cache discipline, not urllib.
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agentlab import providers  # noqa: E402
from agentlab.model import SimModel  # noqa: E402
from agentlab.providers import OpenRouterModel, ProviderError, make_provider  # noqa: E402

CANNED = {
    "choices": [
        {"message": {"content": '{"vendor": "Acme"}'}, "finish_reason": "stop"}
    ],
    "usage": {"prompt_tokens": 40, "completion_tokens": 12, "cost": 0.00021},
}


class TestFactory(unittest.TestCase):
    def test_sim_is_default(self):
        model = make_provider(None, corpus_texts=["a"], seed=3)
        self.assertIsInstance(model, SimModel)

    def test_unknown_provider(self):
        with self.assertRaises(ProviderError):
            make_provider("telepathy")

    def test_openrouter_requires_model_id(self):
        with self.assertRaises(ProviderError):
            make_provider("openrouter", api_key="k")


class TestOpenRouterGuardrails(unittest.TestCase):
    def test_missing_key_is_a_clear_error(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENROUTER_API_KEY", None)
            with self.assertRaises(ProviderError) as ctx:
                OpenRouterModel("vendor/model")
        self.assertIn("OPENROUTER_API_KEY", str(ctx.exception))

    def test_key_is_not_required_in_argv(self):
        model = OpenRouterModel("vendor/model", api_key="secret")
        self.assertEqual(model.model_id, "vendor/model")


class TestCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(providers, "CACHE_ROOT", pathlib.Path(self.tmp.name))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def _model(self, **kwargs):
        return OpenRouterModel("vendor/model", api_key="secret", **kwargs)

    def test_second_identical_call_is_free(self):
        model = self._model()
        model._request = mock.Mock(return_value=CANNED)

        first = model.complete("extract")
        self.assertFalse(first.cached)
        self.assertAlmostEqual(first.cost_usd, 0.00021)

        again = self._model()
        again._request = mock.Mock(side_effect=AssertionError("should not hit the network"))
        second = again.complete("extract")

        self.assertTrue(second.cached)
        self.assertEqual(second.cost_usd, 0.0)
        self.assertEqual(second.text, first.text)
        self.assertEqual(again.cache_hits, 1)

    def test_changed_prompt_is_not_cached(self):
        self._model()._request = mock.Mock(return_value=CANNED)
        model = self._model()
        model._request = mock.Mock(return_value=CANNED)
        model.complete("a")
        model.complete("b")
        self.assertEqual(model.cache_hits, 0)

    def test_changed_temperature_is_not_cached(self):
        model = self._model(temperature=0.0)
        model._request = mock.Mock(return_value=CANNED)
        model.complete("a")
        hotter = self._model(temperature=0.7)
        hotter._request = mock.Mock(return_value=CANNED)
        hotter.complete("a")
        self.assertEqual(hotter.cache_hits, 0)

    def test_cache_can_be_disabled(self):
        model = self._model(use_cache=False)
        model._request = mock.Mock(return_value=CANNED)
        model.complete("a")
        model.complete("a")
        self.assertEqual(model.cache_hits, 0)
        self.assertEqual(model._request.call_count, 2)

    def test_partial_usage_still_accounts(self):
        model = self._model()
        model._request = mock.Mock(
            return_value={
                "choices": [{"message": {"content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 0},
            }
        )
        response = model.complete("a")
        self.assertAlmostEqual(response.cost_usd, 1.0, places=4)

    def test_accounting_matches_contract(self):
        model = self._model()
        model._request = mock.Mock(return_value=CANNED)
        model.complete("a")
        self.assertEqual(model.n_calls, 1)
        self.assertEqual(len(model.latencies), 1)
        self.assertAlmostEqual(model.cost_usd, 0.00021)
        model.reset()
        self.assertEqual(model.n_calls, 0)
        self.assertEqual(model.cost_usd, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
