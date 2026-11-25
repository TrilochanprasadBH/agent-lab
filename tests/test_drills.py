"""Every drill must be fair and solvable.

These are the tests that stop the lab from quietly rotting: a drill whose baseline
already passes teaches nothing, and a drill whose reference fails is unsolvable
and will waste a week of someone's practice time.
"""

from __future__ import annotations

import importlib
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agentlab.drill import run_drill  # noqa: E402

DRILLS = [
    "w01_extraction",
    "w02_retrieval",
    "w03_packing",
    "w04_tools",
    "w05_loop",
    "w06_evals",
    "w07_judge",
    "w08_routing",
    "w09_injection",
    "w10_triage",
    "w11_capstone",
    "w12_significance",
    "w13_sets",
    "w14_trajectory",
    "w15_regression",
    "w16_semantic_cache",
    "w17_pii",
]


def load_reference(drill_name: str):
    prefix = drill_name.split("_")[0]
    path = ROOT / "solutions" / f"{prefix}_reference.py"
    spec = importlib.util.spec_from_file_location(f"{prefix}_ref", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(drill_name: str, task):
    module = importlib.import_module(f"drills.{drill_name}.drill")
    items = module.corpus()
    model = module.build_model()
    results = run_drill(items, task, model)
    card = module.score(results, model, module.TARGET_ACCURACY, module.MAX_COST_USD)
    return card, module


class TestEveryDrill(unittest.TestCase):
    def test_baseline_does_not_already_pass(self):
        for name in DRILLS:
            with self.subTest(drill=name):
                module = importlib.import_module(f"drills.{name}.drill")
                task_module = importlib.import_module(f"drills.{name}.task")
                task = getattr(task_module, module.TASK_NAME)
                card, _ = run(name, task)
                self.assertFalse(
                    card.passed,
                    f"{name}: baseline already passes at {card.accuracy:.1%}",
                )
                self.assertEqual(card.crashes, 0, f"{name}: baseline should not crash")

    def test_reference_solution_passes(self):
        for name in DRILLS:
            with self.subTest(drill=name):
                module = importlib.import_module(f"drills.{name}.drill")
                reference = getattr(load_reference(name), module.TASK_NAME)
                card, _ = run(name, reference)
                self.assertTrue(
                    card.meets_accuracy,
                    f"{name}: reference only reached {card.accuracy:.1%} "
                    f"(target {card.target_accuracy:.0%})",
                )
                self.assertTrue(
                    card.meets_cost,
                    f"{name}: reference cost ${card.cost_usd:.4f} "
                    f"over cap ${card.max_cost_usd:.4f}",
                )
                self.assertEqual(card.crashes, 0, f"{name}: reference crashed")

    def test_reference_is_deterministic(self):
        for name in DRILLS:
            with self.subTest(drill=name):
                module = importlib.import_module(f"drills.{name}.drill")
                reference = getattr(load_reference(name), module.TASK_NAME)
                first, _ = run(name, reference)
                second, _ = run(name, reference)
                self.assertAlmostEqual(
                    first.accuracy,
                    second.accuracy,
                    places=6,
                    msg=f"{name}: scores differ between identical runs",
                )

    def test_every_drill_has_a_spec(self):
        for name in DRILLS:
            with self.subTest(drill=name):
                spec = ROOT / "drills" / name / "spec.md"
                self.assertTrue(spec.exists(), f"{name} has no spec.md")


if __name__ == "__main__":
    unittest.main(verbosity=2)
