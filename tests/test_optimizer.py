from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from bo.metric import rgb_distance
from bo.prior import GaussianProcess, gaussian_process_prior
from bo.sampling import select_next_rgb
from utils.artifacts import write_history, write_summary
from utils.campaign import (
    OptimizationConfig,
    OptimizationResult,
    run_optimization,
)
from utils.cli import main


def test_covariance(left: np.ndarray, right: np.ndarray, _length: float) -> np.ndarray:
    """A deliberately non-workshop kernel used only to test orchestration."""
    return 1.0 + (left @ right.T) / (3.0 * 255.0**2)


def test_metric(_target, measured) -> float:
    """A test double, not the workshop RGB-distance solution."""
    return float(measured[0])


def test_sampler(_model, _points, _costs, candidates, _exploration):
    """A deterministic test double, not the workshop acquisition solution."""
    return candidates[0]


class WorkshopExerciseTests(unittest.TestCase):
    def test_source_has_only_web_utils_and_bo_feature_folders(self):
        source = Path(__file__).parents[1] / "src"
        folders = sorted(
            path.name
            for path in source.iterdir()
            if path.is_dir()
            and not path.name.startswith("__")
            and not path.name.endswith(".egg-info")
        )
        self.assertEqual(folders, ["bo", "utils", "web"])
        bo_files = sorted(path.name for path in (source / "bo").glob("*.py"))
        self.assertEqual(
            bo_files,
            ["__init__.py", "metric.py", "prior.py", "sampling.py"],
        )

    def test_all_three_exercises_are_explicit_stubs(self):
        with self.assertRaisesRegex(NotImplementedError, "bo/metric.py"):
            rgb_distance((1, 2, 3), (4, 5, 6))
        with self.assertRaisesRegex(NotImplementedError, "bo/prior.py"):
            gaussian_process_prior(np.zeros((1, 3)), np.zeros((1, 3)), 45.0)
        with self.assertRaisesRegex(NotImplementedError, "bo/sampling.py"):
            select_next_rgb(
                mock.Mock(),
                np.zeros((2, 3)),
                np.zeros(2),
                np.zeros((1, 3)),
                0.1,
            )

        source = Path(__file__).parents[1] / "src" / "bo"
        for filename in ("metric.py", "prior.py", "sampling.py"):
            self.assertIn("Put your solution here", (source / filename).read_text())

    def test_cli_reports_an_incomplete_exercise_without_a_traceback(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            mock.patch(
                "utils.cli.measurement_function",
                return_value=lambda _red, _green, _blue: (10, 20, 30),
            ),
            mock.patch("sys.stderr") as stderr,
        ):
            status = main(
                [
                    "#102030",
                    "--iterations",
                    "3",
                    "--initial",
                    "2",
                    "--candidates",
                    "100",
                    "--no-plot",
                    "--output",
                    temporary,
                ]
            )
        self.assertEqual(status, 3)
        self.assertIn("workshop exercise incomplete", str(stderr.write.call_args_list))


class GaussianProcessInfrastructureTests(unittest.TestCase):
    def test_posterior_uses_an_injected_prior(self):
        points = np.array(
            [[0.0, 0.0, 0.0], [64.0, 128.0, 192.0], [255.0, 255.0, 255.0]]
        )
        costs = np.array([200.0, 10.0, 120.0])
        model = GaussianProcess(
            length_scale=45,
            noise=1e-9,
            prior=test_covariance,
        ).fit(points, costs)
        mean, deviation = model.posterior(points)
        self.assertEqual(mean.shape, (3,))
        self.assertEqual(deviation.shape, (3,))
        self.assertTrue(np.all(np.isfinite(mean)))
        self.assertTrue(np.all(deviation > 0))

    def test_gaussian_process_rejects_non_rgb_inputs(self):
        with self.assertRaisesRegex(ValueError, "red, green, blue"):
            GaussianProcess(prior=test_covariance).fit(
                np.array([[0.0, 0.0], [1.0, 1.0]]), np.array([0.1, 0.2])
            )


class CampaignTests(unittest.TestCase):
    def test_dependencies_can_be_completed_and_campaign_minimizes_cost(self):
        config = OptimizationConfig(
            total_iterations=5,
            initial_points=3,
            seed=11,
            candidate_count=100,
        )

        def measurement(red, green, blue):
            return round(red), round(green), round(blue)

        first = run_optimization(
            measurement,
            (0, 0, 0),
            config,
            metric=test_metric,
            prior=test_covariance,
            sampler=test_sampler,
        )
        second = run_optimization(
            measurement,
            (0, 0, 0),
            config,
            metric=test_metric,
            prior=test_covariance,
            sampler=test_sampler,
        )
        np.testing.assert_allclose(first.points, second.points)
        np.testing.assert_allclose(first.costs, second.costs)
        self.assertEqual(first.points.shape, (5, 3))
        self.assertEqual(first.measurements.shape, (5, 3))
        self.assertEqual(first.best_distance, float(first.costs.min()))
        self.assertTrue(np.all(first.points >= 0))
        self.assertTrue(np.all(first.points <= 255))

    def test_writes_rgb_distance_artifacts(self):
        result = OptimizationResult(
            points=np.array([[10.0, 20.0, 30.0], [40.0, 50.0, 60.0]]),
            measurements=np.array([[9, 19, 29], [38, 49, 61]]),
            costs=np.array([4.0, 2.5]),
            phases=("initial", "bayesian"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            write_history(
                directory,
                result.points,
                result.measurements,
                result.costs,
                result.phases,
            )
            write_summary(directory, result, seed=2026, target_rgb=(40, 50, 60))
            with (directory / "history.csv").open(newline="") as handle:
                self.assertEqual(
                    next(csv.reader(handle)),
                    [
                        "iteration",
                        "phase",
                        "led_red",
                        "led_green",
                        "led_blue",
                        "sensor_red",
                        "sensor_green",
                        "sensor_blue",
                        "rgb_distance",
                        "best_distance",
                    ],
                )
            summary = json.loads((directory / "summary.json").read_text())
            self.assertEqual(summary["iterations"], 2)
            self.assertEqual(summary["target_rgb"], [40, 50, 60])
            self.assertEqual(summary["best_distance"], 2.5)


if __name__ == "__main__":
    unittest.main()
