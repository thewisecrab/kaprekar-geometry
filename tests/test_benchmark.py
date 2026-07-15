from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import tempfile
import unittest
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None


@unittest.skipIf(np is None, "NumPy benchmark extra is not installed")
class BenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        from kaprekar.benchmark import binary_metrics, feature_families, load_split, run_benchmark

        self.binary_metrics = binary_metrics
        self.feature_families = feature_families
        self.load_split = load_split
        self.run_benchmark = run_benchmark

    @staticmethod
    def _write_split(directory: Path, name: str, seed: int, samples: int = 80) -> Path:
        rng = np.random.default_rng(seed)
        logits = rng.normal(size=(samples, 7))
        signal = logits[:, 0] - logits[:, 1] + 0.35 * rng.normal(size=samples)
        labels = (signal > np.median(signal)).astype(np.int64)
        hidden = np.column_stack((signal, rng.normal(size=samples)))
        sample_ids = np.asarray([f"{name}-{index}" for index in range(samples)])
        group_ids = np.asarray(
            [f"{name}-group-{index // 2}" for index in range(samples)]
        )
        path = directory / f"{name}.npz"
        np.savez(
            path,
            logits=logits,
            labels=labels,
            hidden=hidden,
            sample_ids=sample_ids,
            group_ids=group_ids,
        )
        return path

    def test_end_to_end_benchmark_uses_three_disjoint_splits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            train = self._write_split(directory, "train", 1)
            calibration = self._write_split(directory, "calibration", 2)
            test = self._write_split(directory, "test", 3)

            result = self.run_benchmark(
                train,
                calibration,
                test,
                k=4,
                bootstrap_replicates=30,
            )

        self.assertEqual(result["schema_version"], "1.1")
        self.assertIn("not_universal", result["evidence_scope"])
        expected = {
            "max_probability",
            "negative_entropy",
            "top1_margin",
            "raw_sorted_top_k",
            "sorted_top_k_probabilities",
            "kgs",
            "output_hybrid",
            "output_plus_hidden",
        }
        self.assertEqual(set(result["models"]), expected)
        for model in result["models"].values():
            metrics = model["metrics"]
            self.assertEqual(model["fit_diagnostics"]["status"], "converged")
            self.assertGreaterEqual(metrics["auroc"], 0.0)
            self.assertLessEqual(metrics["auroc"], 1.0)
            self.assertGreaterEqual(
                metrics["empirical_coverage_at_target_risk"], 0.0
            )
            self.assertLessEqual(
                metrics["empirical_coverage_at_target_risk"], 1.0
            )
            self.assertEqual(len(model["test_probabilities"]), 80)
            self.assertEqual(
                model["bootstrap_intervals"]["auroc"]["replicates"],
                30,
            )
            self.assertEqual(
                model["bootstrap_intervals"]["auroc"]["resampling_unit"],
                "dependency_group",
            )

    def test_cli_benchmark_summary_is_machine_readable(self) -> None:
        from kaprekar.cli import main

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            train = self._write_split(directory, "train", 11, samples=30)
            calibration = self._write_split(directory, "calibration", 12, samples=30)
            test = self._write_split(directory, "test", 13, samples=30)
            output = StringIO()
            with redirect_stdout(output):
                status = main(
                    [
                        "benchmark",
                        "--train",
                        str(train),
                        "--calibration",
                        str(calibration),
                        "--test",
                        str(test),
                        "--top-k",
                        "4",
                        "--bootstrap-replicates",
                        "10",
                        "--summary-only",
                    ]
                )

        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertIn("raw_sorted_top_k", payload["models"])
        self.assertNotIn("test_sample_ids", payload)
        self.assertNotIn("test_group_ids", payload)
        self.assertNotIn(
            "test_probabilities",
            payload["models"]["kgs"],
        )

    def test_sample_id_overlap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            train = self._write_split(directory, "train", 4)
            calibration = self._write_split(directory, "calibration", 5)
            test = self._write_split(directory, "test", 6)
            with np.load(train, allow_pickle=False) as archive:
                arrays = {name: archive[name] for name in archive.files}
            arrays["sample_ids"] = arrays["sample_ids"].astype("<U32")
            arrays["sample_ids"][0] = "calibration-0"
            np.savez(train, **arrays)

            with self.assertRaisesRegex(ValueError, "leakage"):
                self.run_benchmark(train, calibration, test, k=3)

    def test_dependency_group_overlap_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            train = self._write_split(directory, "train", 31)
            calibration = self._write_split(directory, "calibration", 32)
            test = self._write_split(directory, "test", 33)
            with np.load(train, allow_pickle=False) as archive:
                arrays = {name: archive[name] for name in archive.files}
            arrays["group_ids"] = arrays["group_ids"].astype("<U32")
            arrays["group_ids"][0] = "calibration-group-0"
            np.savez(train, **arrays)

            with self.assertRaisesRegex(ValueError, "group leakage"):
                self.run_benchmark(train, calibration, test, k=3)

    def test_flat_rows_have_explicit_mask_and_finite_features(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "flat.npz"
            np.savez(
                path,
                logits=np.asarray([[1.0, 1.0, 1.0], [2.0, 1.0, 0.0]]),
                labels=np.asarray([0, 1]),
                sample_ids=np.asarray(["a", "b"]),
                group_ids=np.asarray(["g-a", "g-b"]),
            )
            split = self.load_split(path)
            features = self.feature_families(split, k=3)

        self.assertTrue(np.isfinite(features["kgs"]).all())
        self.assertEqual(features["kgs"][0, -1], 1.0)
        self.assertEqual(features["kgs"][1, -1], 0.0)
        self.assertEqual(features["raw_sorted_top_k"][0, -1], 1.0)
        self.assertEqual(
            features["raw_sorted_top_k"].shape[1],
            features["kgs"].shape[1],
        )
        with self.assertRaises(ValueError):
            self.feature_families(split, k=1)

    def test_metrics_recognize_perfect_ranking(self) -> None:
        metrics = self.binary_metrics(
            np.asarray([0.0, 0.0, 1.0, 1.0]),
            np.asarray([0.1, 0.2, 0.8, 0.9]),
            ece_bins=2,
        )

        self.assertEqual(metrics["auroc"], 1.0)
        self.assertEqual(metrics["average_precision"], 1.0)

    def test_tied_score_metrics_are_row_order_invariant(self) -> None:
        probabilities = np.full(8, 0.5)
        first = self.binary_metrics(
            np.asarray([1, 1, 1, 1, 0, 0, 0, 0]),
            probabilities,
            ece_bins=4,
            target_risk=0.4,
        )
        second = self.binary_metrics(
            np.asarray([1, 0, 1, 0, 1, 0, 1, 0]),
            probabilities,
            ece_bins=4,
            target_risk=0.4,
        )

        for metric in (
            "ece_equal_frequency",
            "aurc",
            "empirical_coverage_at_target_risk",
        ):
            self.assertEqual(first[metric], second[metric])
        self.assertEqual(first["ece_equal_frequency"], 0.0)
        self.assertEqual(first["aurc"], 0.5)
        self.assertEqual(first["empirical_coverage_at_target_risk"], 0.0)

    def test_invalid_archive_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.npz"
            np.savez(path, logits=np.ones((2, 2)), labels=np.asarray([0, 1]))

            with self.assertRaisesRegex(ValueError, "sample_ids"):
                self.load_split(path)

    def test_zero_regularization_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            train = self._write_split(directory, "train", 21)
            calibration = self._write_split(directory, "calibration", 22)
            test = self._write_split(directory, "test", 23)

            with self.assertRaisesRegex(ValueError, "strictly positive"):
                self.run_benchmark(
                    train,
                    calibration,
                    test,
                    k=4,
                    regularization=0.0,
                    bootstrap_replicates=5,
                )


if __name__ == "__main__":
    unittest.main()
