"""Fail if a number in the README no longer matches a drill.

    python3 -m unittest tests.test_documented_numbers -v

The lab quotes a baseline and a reference score for every drill. Those numbers are the whole
promise of the place — "run it and you get a number" — and until now nothing checked them. The
`triage` audit found six that had drifted; this test is the version of that lesson applied one
project earlier.

It parses the README table, runs each drill twice (the shipped task, then the reference
solution), and compares. A drill added to `DRILLS` without a README row fails. A README row
without a drill fails. A number that moved fails with both values in the message.

Two rows cannot be parsed as "X% → Y%" because their point is not a percentage: `w08` starts at
100% accuracy and fails on cost. Those are listed in `OVERRIDES`, deliberately and visibly,
rather than loosening the parser until anything matches.
"""

from __future__ import annotations

import importlib
import importlib.util
import pathlib
import re
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
    "w18_constrained_json",
    "w19_memory",
    "w20_debug",
]

# Rows whose baseline → reference cell is not a percentage pair. `w08` starts at 100% accuracy
# and loses on cost, so its entry is (baseline, reference) in words, checked by `test_w08_cost`.
OVERRIDES: dict[str, tuple[str, str]] = {"08": ("100%", "100%")}

ROW = re.compile(
    r"^\|\s*(\d{2})\s*\|\s*([^|]+?)\s*\|[^|]*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$"
)
PAIR = re.compile(r"(\d+(?:\.\d+)?)%\s*→\s*(\d+(?:\.\d+)?)%")
TARGET = re.compile(r"(\d+)%")


def readme_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if not match:
            continue
        number, name, pair, target = match.groups()
        rows[number] = {"name": name.strip(), "pair": pair.strip(), "target": target.strip()}
    return rows


def row_key(drill_name: str) -> str:
    """`w07_judge` -> `07`, the key used in the README table."""
    return drill_name.split("_")[0][1:]


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
    return module.score(results, model, module.TARGET_ACCURACY, module.MAX_COST_USD), module


def pct(value: float) -> str:
    return f"{round(value * 100, 1)}%"


class TestDocumentedNumbers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = readme_rows()

    def test_every_drill_has_a_row_and_every_row_has_a_drill(self):
        documented = set(self.rows)
        expected = {row_key(name) for name in DRILLS}
        self.assertEqual(
            documented - expected, set(), "README documents drills that do not exist"
        )
        self.assertEqual(
            expected - documented, set(), "drills are missing from the README table"
        )

    def test_baseline_and_reference_match_the_readme(self):
        for name in DRILLS:
            number = row_key(name)
            with self.subTest(drill=name):
                row = self.rows[number]
                if number in OVERRIDES:
                    self.assertIn(OVERRIDES[number][0], row["pair"], name)
                    self.assertIn(OVERRIDES[number][1], row["pair"], name)
                    continue

                match = PAIR.search(row["pair"])
                self.assertIsNotNone(match, f"{name}: unparseable pair {row['pair']!r}")
                baseline_doc, reference_doc = match.group(1) + "%", match.group(2) + "%"

                module = importlib.import_module(f"drills.{name}.drill")
                baseline = getattr(importlib.import_module(f"drills.{name}.task"), module.TASK_NAME)
                reference = getattr(load_reference(name), module.TASK_NAME)

                baseline_card, _ = run(name, baseline)
                reference_card, _ = run(name, reference)

                self.assertAlmostEqual(
                    baseline_card.accuracy * 100, float(baseline_doc.rstrip("%")),
                    delta=0.10,
                    msg=f"{name}: baseline scores {pct(baseline_card.accuracy)}, "
                        f"README says {baseline_doc}",
                )
                self.assertAlmostEqual(
                    reference_card.accuracy * 100, float(reference_doc.rstrip("%")),
                    delta=0.10,
                    msg=f"{name}: reference scores {pct(reference_card.accuracy)}, "
                        f"README says {reference_doc}",
                )

    def test_targets_match_the_readme(self):
        for name in DRILLS:
            number = row_key(name)
            with self.subTest(drill=name):
                module = importlib.import_module(f"drills.{name}.drill")
                documented = TARGET.match(self.rows[number]["target"])
                self.assertIsNotNone(documented, f"{name}: unparseable target")
                self.assertEqual(
                    f"{int(documented.group(1))}%",
                    f"{round(module.TARGET_ACCURACY * 100)}%",
                    f"{name}: target is {module.TARGET_ACCURACY:.0%}, README says "
                    f"{documented.group(1)}%",
                )

    def test_w08_is_the_only_row_that_needed_an_override(self):
        # If a new row stops parsing, the fix is to make its number precise, not to add it here.
        unparsed = [
            number
            for number, row in self.rows.items()
            if number not in OVERRIDES and not PAIR.search(row["pair"])
        ]
        self.assertEqual(unparsed, [], f"rows with no percentage pair: {unparsed}")


class TestDocumentedClaims(unittest.TestCase):
    """The sentences in the README that a table cannot check."""

    def test_every_drill_builds_its_model_with_no_key_and_no_network(self):
        # Some drills can be pointed at a real provider with --provider; none of them need one.
        # `build_model` is what `run.py` calls for the default provider, so calling it with an
        # empty environment is the check that the offline promise holds.
        import os
        from unittest import mock

        for name in DRILLS:
            with self.subTest(drill=name):
                module = importlib.import_module(f"drills.{name}.drill")
                with mock.patch.dict(os.environ, {}, clear=True):
                    model = module.build_model()
                # Not every drill's world is a chat model: w19 answers from a memory it is
                # handed, w02 embeds and searches, and w20 reads traces and calls nothing at all.
                # What matters is that the object came back with no key and no network, not that
                # it has a particular method.
                interfaces = ("complete", "answer", "search", "embed")
                has_interface = any(callable(getattr(model, name, None)) for name in interfaces)
                no_model = getattr(model, "n_calls", None) == 0
                self.assertTrue(has_interface or no_model, name)

    def test_every_drill_has_a_spec_and_a_reference(self):
        for name in DRILLS:
            prefix = name.split("_")[0]
            with self.subTest(drill=name):
                self.assertTrue((ROOT / "drills" / name / "spec.md").exists(), name)
                self.assertTrue((ROOT / "solutions" / f"{prefix}_reference.py").exists(), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
