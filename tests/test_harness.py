"""Harness tests.

The drill is only useful if the number means something, so these check the
things that would silently corrupt every score: determinism, normalization,
and whether the target is actually reachable.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agentlab.drill import run_drill  # noqa: E402
from agentlab.evals import matches, norm_date, norm_money, norm_text  # noqa: E402
from agentlab.model import SimModel  # noqa: E402
from drills.w01_extraction.data import generate  # noqa: E402
from drills.w01_extraction.task import extract as baseline  # noqa: E402


def load_reference():
    path = ROOT / "solutions" / "w01_reference.py"
    spec = importlib.util.spec_from_file_location("w01_reference", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.extract


class TestCorpus(unittest.TestCase):
    def test_deterministic(self):
        a, b = generate(), generate()
        self.assertEqual([i.raw for i in a], [i.raw for i in b])

    def test_unique_ids(self):
        ids = [i.doc_id for i in generate()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_truth_is_internally_consistent(self):
        for inv in generate():
            t = inv.truth
            self.assertAlmostEqual(t["subtotal"] + t["tax"], t["total"], places=2)


class TestModel(unittest.TestCase):
    def test_same_prompt_same_attempt_is_stable(self):
        corpus = generate()[:4]
        model = SimModel([i.raw for i in corpus])
        first = model.complete("Document:\n" + corpus[0].raw).text
        model2 = SimModel([i.raw for i in corpus])
        again = model2.complete("Document:\n" + corpus[0].raw).text
        self.assertEqual(first, again)

    def test_no_document_in_prompt_does_not_crash(self):
        model = SimModel([i.raw for i in generate()[:3]])
        response = model.complete("hello")
        self.assertIn("couldn't find", response.text)

    def test_accounting(self):
        model = SimModel([i.raw for i in generate()[:3]])
        model.complete("Document:\n" + generate()[0].raw)
        self.assertEqual(model.n_calls, 1)
        self.assertGreater(model.cost_usd, 0)
        self.assertEqual(len(model.latencies), 1)


class TestNormalization(unittest.TestCase):
    def test_thousands_separator(self):
        self.assertAlmostEqual(norm_money("1,350.00 USD"), 1350.00)

    def test_decimal_comma(self):
        self.assertAlmostEqual(norm_money("1.350,00 EUR"), 1350.00)

    def test_plain_thousands(self):
        self.assertAlmostEqual(norm_money("1,350"), 1350.0)

    def test_symbol(self):
        self.assertAlmostEqual(norm_money("$4,116.55"), 4116.55)

    def test_date_formats_agree(self):
        expected = norm_date("2026-03-12")
        for text in ("12 March 2026", "March 12, 2026", "12/03/2026"):
            self.assertEqual(norm_date(text), expected, text)

    def test_vendor_punctuation_is_ignored(self):
        self.assertEqual(norm_text("Acme Corp."), norm_text("acme corp"))

    def test_total_tolerance(self):
        self.assertTrue(matches("total", 1350.004, 1350.00))
        self.assertFalse(matches("total", 1350.05, 1350.00))

    def test_none_never_matches(self):
        for field in ("vendor", "currency", "invoice_date", "total"):
            self.assertFalse(matches(field, None, "anything"), field)


class TestDrillIntegrity(unittest.TestCase):
    """If these fail, the drill is unfair or unsolvable."""

    @classmethod
    def setUpClass(cls):
        cls.corpus = generate()

    def _run(self, task):
        model = SimModel([i.raw for i in self.corpus])
        return run_drill(
            self.corpus, task, model, target_accuracy=0.90, max_cost_usd=0.012
        )[0]

    def test_baseline_is_not_already_passing(self):
        card = self._run(baseline)
        self.assertLess(card.accuracy, 0.85)
        self.assertEqual(card.crashes, 0)

    def test_reference_solution_reaches_target(self):
        card = self._run(load_reference())
        self.assertGreaterEqual(card.accuracy, 0.95)
        self.assertLessEqual(card.cost_usd, 0.012)
        self.assertTrue(card.passed)

    def test_bypassing_the_model_is_rejected(self):
        card = self._run(lambda doc, model: {})
        self.assertEqual(card.calls, 0)
        self.assertFalse(card.uses_model)
        self.assertFalse(card.passed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
