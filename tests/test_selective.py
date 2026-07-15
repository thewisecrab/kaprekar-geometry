from __future__ import annotations

from math import isclose
import unittest

from kaprekar.selective import (
    apply_abstention,
    calibrate_selective_risk,
    clopper_pearson_upper,
)


class SelectiveRiskTests(unittest.TestCase):
    def test_zero_error_upper_bound_matches_closed_form(self) -> None:
        bound = clopper_pearson_upper(0, 100, alpha=0.05)
        expected = 1.0 - 0.05 ** (1.0 / 100.0)

        self.assertTrue(isclose(bound, expected, rel_tol=1e-11, abs_tol=1e-11))
        self.assertEqual(clopper_pearson_upper(10, 10), 1.0)

    def test_separated_confidences_yield_a_safe_nontrivial_policy(self) -> None:
        confidences = [0.95] * 100 + [0.05] * 100
        correctness = [1] * 100 + [0] * 100

        result = calibrate_selective_risk(
            confidences,
            correctness,
            target_risk=0.10,
            confidence_level=0.95,
            threshold_count=101,
            min_accepted=30,
        )

        self.assertEqual(result.status, "calibrated")
        self.assertEqual(result.calibration_accepted, 100)
        self.assertEqual(result.calibration_errors, 0)
        self.assertLessEqual(result.risk_upper_bound or 1.0, 0.10)
        self.assertIn("IID", result.assumption)
        self.assertIn("exchangeability is insufficient", result.assumption)
        decisions = apply_abstention([0.99, 0.05, 0.01], result)
        self.assertEqual(decisions, (True, False, False))

    def test_no_safe_threshold_fails_closed(self) -> None:
        result = calibrate_selective_risk(
            [0.9] * 50 + [0.1] * 50,
            [0] * 100,
            target_risk=0.05,
            min_accepted=20,
        )

        self.assertEqual(result.status, "no_safe_threshold")
        self.assertIsNone(result.threshold)
        with self.assertRaisesRegex(ValueError, "no safe threshold"):
            apply_abstention([0.9], result)

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            clopper_pearson_upper(2, 1)
        with self.assertRaises(ValueError):
            calibrate_selective_risk([0.5], [1], target_risk=0.1)
        with self.assertRaises(ValueError):
            calibrate_selective_risk([0.5, 0.6], [1, 2], target_risk=0.1)


if __name__ == "__main__":
    unittest.main()
