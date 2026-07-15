from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from kaprekar.cli import main
from kaprekar.core import ComputationLimitError
from kaprekar.verification import verify_case, verify_ranges


ROOT = Path(__file__).resolve().parents[1]


class VerificationTests(unittest.TestCase):
    def test_exhaustive_report_is_structured_and_exact(self) -> None:
        report = verify_ranges(2, 4, 1, 5, mode="exhaustive")
        self.assertTrue(report.passed)
        self.assertEqual(len(report.cases), 15)
        self.assertEqual(
            report.total_states_checked,
            sum(b**n for b in range(2, 5) for n in range(1, 6)),
        )
        for case in report.cases:
            self.assertEqual(case.factorization_scope, "all_raw_states")
            self.assertTrue(case.image_cardinality_verified)
            self.assertTrue(case.lambda_injective)
            self.assertEqual(case.observed_image_size, case.expected_image_size)

    def test_reduced_report_checks_every_spectrum_representative(self) -> None:
        case = verify_case(10, 10, mode="reduced")
        self.assertTrue(case.passed)
        self.assertEqual(case.states_checked, 2002)
        self.assertEqual(case.factorization_checks, 2002)
        self.assertEqual(case.observed_image_size, 2002)
        self.assertEqual(case.factorization_scope, "one_representative_per_spectrum")

    def test_sampled_report_is_seeded_and_does_not_overclaim(self) -> None:
        first = verify_case(10, 12, mode="sampled", sample_size=250, seed=42)
        second = verify_case(10, 12, mode="sampled", sample_size=250, seed=42)
        self.assertTrue(first.passed)
        self.assertEqual(first.sample_seed, second.sample_seed)
        self.assertEqual(first.sample_sha256, second.sample_sha256)
        self.assertEqual(len(first.sample_sha256), 64)
        self.assertEqual(first.distinct_outputs_observed, second.distinct_outputs_observed)
        self.assertEqual(first.factorization_checks, 250)
        self.assertFalse(first.image_cardinality_verified)
        self.assertIsNone(first.observed_image_size)
        self.assertIsNone(first.lambda_injective)

    def test_invalid_and_empty_ranges_fail_loudly(self) -> None:
        invalid_calls = (
            lambda: verify_ranges(1, 2, 1, 2),
            lambda: verify_ranges(3, 2, 1, 2),
            lambda: verify_ranges(2, 3, 0, 2),
            lambda: verify_ranges(2, 3, 3, 2),
            lambda: verify_ranges(True, 3, 1, 2),
            lambda: verify_ranges(2, 3, 1, 2, force=1),  # type: ignore[arg-type]
        )
        for call in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaises((TypeError, ValueError)):
                    call()

    def test_state_work_case_and_digit_guards(self) -> None:
        with self.assertRaises(ComputationLimitError):
            verify_case(10, 8, mode="exhaustive")
        with self.assertRaises(ComputationLimitError):
            verify_ranges(2, 100_002, 1, 1, mode="sampled", sample_size=1)
        with self.assertRaises(ComputationLimitError):
            verify_case(
                2,
                10_001,
                mode="sampled",
                sample_size=1,
                max_work_units=100_000,
            )
        with self.assertRaises(ComputationLimitError):
            verify_case(2, 100, mode="sampled", sample_size=10, max_work_units=999)

    def test_report_is_json_serializable(self) -> None:
        payload = verify_case(10, 4, mode="reduced").to_dict()
        self.assertEqual(json.loads(json.dumps(payload))["passed"], True)

    def test_cli_json_and_error_status(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = main(
                [
                    "verify",
                    "--base-min",
                    "10",
                    "--base-max",
                    "10",
                    "--digits-min",
                    "4",
                    "--digits-max",
                    "4",
                    "--mode",
                    "reduced",
                    "--json",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["cases"][0]["expected_image_size"], 55)

        output = StringIO()
        with redirect_stdout(output):
            status = main(
                [
                    "verify",
                    "--base-min",
                    "10",
                    "--base-max",
                    "10",
                    "--digits-min",
                    "8",
                    "--digits-max",
                    "8",
                    "--mode",
                    "exhaustive",
                    "--json",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 2)
        self.assertEqual(payload["error"], "ComputationLimitError")

    def test_cli_analyze_json_is_machine_readable(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = main(
                ["analyze", "--base", "10", "--digits", "4", "--json"]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["attractor_count"], 2)
        self.assertNotIn("states", payload)
        self.assertEqual(sum(a["raw_basin_size"] for a in payload["attractors"]), 10**4)

    def test_cli_logits_reports_degeneracy_and_full_distribution(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = main(
                ["logits", "3", "3", "1", "0", "--top-k", "3", "--json"]
            )
        payload = json.loads(output.getvalue())

        self.assertEqual(status, 0)
        self.assertEqual(payload["coordinates"], [0.0, 1.0])
        self.assertFalse(payload["degenerate"])
        self.assertLess(payload["full_distribution"]["top_k_probability_mass"], 1.0)

    def test_backward_compatible_wrapper_runs_from_checkout(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                "import kaprekar_verification as k; print(k.verify_ranges(2,2,1,3))",
            ],
            cwd=ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(
            process.stdout.strip(),
            "[(2, 1, 1, 1), (2, 2, 2, 2), (2, 3, 2, 2)]",
        )

    @unittest.skipUnless(
        os.environ.get("KAPREKAR_RUN_SLOW_TESTS") == "1",
        "set KAPREKAR_RUN_SLOW_TESTS=1 for the full paper grid",
    )
    def test_full_paper_grid(self) -> None:
        report = verify_ranges()
        self.assertTrue(report.passed)
        self.assertEqual(len(report.cases), 49)
        self.assertEqual(report.total_states_checked, 3_816_497)


if __name__ == "__main__":
    unittest.main()
