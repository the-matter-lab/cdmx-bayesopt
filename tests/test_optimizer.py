from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from cdmx_bayesopt.artifacts import write_history, write_summary
from cdmx_bayesopt.gp import GaussianProcess, expected_improvement
from cdmx_bayesopt.objectives import load_objective, synthetic_point, synthetic_surface
from cdmx_bayesopt.runner import OptimizationConfig, run_optimization


class ObjectiveTests(unittest.TestCase):
    def test_surface_vectorizes(self):
        points = np.array([[0.0, 0.0], [1.0, -1.0]])
        values = synthetic_surface(points)
        self.assertEqual(values.shape, (2,))
        self.assertAlmostEqual(values[0], synthetic_point(0.0, 0.0))

    def test_loader(self):
        self.assertIs(load_objective("synthetic"), synthetic_point)
        with self.assertRaises(ValueError):
            load_objective("missing-colon")

    def test_loader_accepts_a_python_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            objective_file = Path(temporary) / "experiment.py"
            objective_file.write_text("def measure(x1, x2):\n    return x1 + x2\n")
            objective = load_objective(f"{objective_file}:measure")
            self.assertEqual(objective(1.25, 2.5), 3.75)


class GaussianProcessTests(unittest.TestCase):
    def test_posterior_is_close_to_observations(self):
        points = np.array([[-1.0, -1.0], [0.0, 0.0], [1.0, 1.0]])
        values = np.array([1.0, 0.0, 1.5])
        model = GaussianProcess(noise=1e-9).fit(points, values)
        mean, deviation = model.posterior(points)
        np.testing.assert_allclose(mean, values, atol=1e-5)
        self.assertTrue(np.all(deviation < 1e-3))

    def test_expected_improvement_is_finite(self):
        result = expected_improvement(
            np.array([0.0, 1.0]), np.array([0.2, 0.3]), best_value=0.5
        )
        self.assertTrue(np.all(np.isfinite(result)))
        self.assertGreater(result[0], result[1])


class RunnerTests(unittest.TestCase):
    def test_campaign_is_deterministic_and_bounded(self):
        config = OptimizationConfig(
            total_iterations=12,
            initial_points=4,
            seed=11,
            candidate_count=500,
        )
        first = run_optimization(synthetic_point, config)
        second = run_optimization(synthetic_point, config)
        np.testing.assert_allclose(first.points, second.points)
        np.testing.assert_allclose(first.values, second.values)
        self.assertEqual(len(first.values), 12)
        self.assertTrue(np.all(first.points >= config.lower_bound))
        self.assertTrue(np.all(first.points <= config.upper_bound))
        self.assertLessEqual(first.best_value, first.values[: config.initial_points].min())

    def test_writes_machine_readable_artifacts(self):
        result = run_optimization(
            synthetic_point,
            OptimizationConfig(total_iterations=7, initial_points=4, candidate_count=300),
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_history(directory, result.points, result.values, result.phases)
            write_summary(directory, result, seed=2026)
            self.assertTrue((directory / "history.csv").is_file())
            summary = json.loads((directory / "summary.json").read_text())
            self.assertEqual(summary["iterations"], 7)


if __name__ == "__main__":
    unittest.main()
