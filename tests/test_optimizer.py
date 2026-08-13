from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from cdmx_bayesopt.artifacts import write_history, write_summary
from cdmx_bayesopt.gp import GaussianProcess, expected_improvement
from cdmx_bayesopt.runner import OptimizationConfig, run_optimization


def color_score(red: float, green: float, blue: float) -> float:
    target = np.array([40.0, 120.0, 210.0])
    rgb = np.array([red, green, blue])
    return float(1.0 - np.mean(((rgb - target) / 255.0) ** 2))


class GaussianProcessTests(unittest.TestCase):
    def test_posterior_is_close_to_rgb_observations(self):
        points = np.array(
            [[0.0, 0.0, 0.0], [64.0, 128.0, 192.0], [255.0, 255.0, 255.0]]
        )
        scores = np.array([0.2, 0.95, 0.4])
        model = GaussianProcess(length_scale=45, noise=1e-9).fit(points, scores)
        mean, deviation = model.posterior(points)
        np.testing.assert_allclose(mean, scores, atol=1e-5)
        self.assertTrue(np.all(deviation < 1e-3))

    def test_expected_improvement_prefers_a_higher_score(self):
        result = expected_improvement(
            np.array([0.8, 0.4]), np.array([0.2, 0.2]), best_score=0.6
        )
        self.assertTrue(np.all(np.isfinite(result)))
        self.assertGreater(result[0], result[1])

    def test_gaussian_process_rejects_non_rgb_inputs(self):
        with self.assertRaisesRegex(ValueError, "red, green, blue"):
            GaussianProcess().fit(
                np.array([[0.0, 0.0], [1.0, 1.0]]), np.array([0.1, 0.2])
            )


class RunnerTests(unittest.TestCase):
    def test_rgb_campaign_is_deterministic_bounded_and_maximizes(self):
        config = OptimizationConfig(
            total_iterations=12,
            initial_points=4,
            seed=11,
            candidate_count=500,
        )
        first = run_optimization(color_score, config)
        second = run_optimization(color_score, config)
        np.testing.assert_allclose(first.points, second.points)
        np.testing.assert_allclose(first.scores, second.scores)
        self.assertEqual(first.points.shape, (12, 3))
        self.assertTrue(np.all(first.points >= 0))
        self.assertTrue(np.all(first.points <= 255))
        self.assertGreaterEqual(
            first.best_score, first.scores[: config.initial_points].max()
        )

    def test_writes_rgb_sensor_artifacts(self):
        result = run_optimization(
            color_score,
            OptimizationConfig(
                total_iterations=7, initial_points=4, candidate_count=300
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_history(directory, result.points, result.scores, result.phases)
            write_summary(directory, result, seed=2026)
            with (directory / "history.csv").open(newline="") as handle:
                self.assertEqual(
                    next(csv.reader(handle)),
                    [
                        "iteration",
                        "phase",
                        "red",
                        "green",
                        "blue",
                        "sensor_score",
                        "best_so_far",
                    ],
                )
            summary = json.loads((directory / "summary.json").read_text())
            self.assertEqual(summary["iterations"], 7)
            self.assertIn("best_rgb", summary)
            self.assertIn("best_score", summary)


if __name__ == "__main__":
    unittest.main()
