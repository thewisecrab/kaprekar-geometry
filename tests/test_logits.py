from __future__ import annotations

import math
import unittest

from kaprekar.logits import (
    conditional_accepted_distribution,
    gap_simplex,
    reconstruct_sorted_logits,
    relaxed_margin_diagnostic,
    tail_mass_bounds,
)


class GapSimplexTests(unittest.TestCase):
    def test_coordinates_reconstruct_sorted_logits(self) -> None:
        summary = gap_simplex([1.0, 7.0, 3.0, -1.0], k=4)

        self.assertEqual(summary.top_indices, (1, 2, 0, 3))
        self.assertEqual(summary.sorted_logits, (7.0, 3.0, 1.0, -1.0))
        self.assertAlmostEqual(sum(summary.coordinates or ()), 1.0)
        reconstructed = reconstruct_sorted_logits(
            summary.spread,
            summary.coordinates or (),
            anchor=summary.sorted_logits[-1],
        )
        self.assertEqual(reconstructed, summary.sorted_logits)

    def test_affine_invariance_and_spread_scale(self) -> None:
        original = gap_simplex([4.0, 2.0, 1.0, -3.0])
        transformed = gap_simplex([15.0, 11.0, 9.0, 1.0])

        self.assertEqual(original.coordinates, transformed.coordinates)
        self.assertEqual(transformed.spread, 2.0 * original.spread)

    def test_common_offset_is_discarded_but_relative_logits_are_preserved(self) -> None:
        low_offset = gap_simplex([2.0, 1.0])
        high_offset = gap_simplex([102.0, 101.0])

        self.assertEqual(low_offset.coordinates, high_offset.coordinates)
        self.assertEqual(low_offset.spread, high_offset.spread)
        self.assertNotEqual(low_offset.sorted_logits, high_offset.sorted_logits)
        self.assertEqual(
            tuple(value - low_offset.sorted_logits[-1] for value in low_offset.sorted_logits),
            tuple(value - high_offset.sorted_logits[-1] for value in high_offset.sorted_logits),
        )

    def test_rank_probability_ratio_is_exact(self) -> None:
        summary = gap_simplex([5.0, 3.5, 2.0, 0.0])

        self.assertAlmostEqual(summary.probability_ratio(3), math.exp(2.0 - 5.0))

    def test_flat_logits_are_explicitly_degenerate(self) -> None:
        summary = gap_simplex([2.0, 2.0, 2.0], k=3)

        self.assertTrue(summary.degenerate)
        self.assertIsNone(summary.coordinates)
        with self.assertRaisesRegex(ValueError, "undefined"):
            summary.normalized_loss(2)
        self.assertEqual(summary.probability_ratio(2), 1.0)

    def test_k_two_has_no_shape_degrees_of_freedom(self) -> None:
        summary = gap_simplex([3.0, 1.0, -4.0], k=2)

        self.assertEqual(summary.coordinates, (1.0,))
        self.assertEqual(summary.shape_degrees_of_freedom, 0)

    def test_ties_are_sorted_by_original_index(self) -> None:
        summary = gap_simplex([1.0, 3.0, 3.0, 0.0], k=3)

        self.assertEqual(summary.top_indices, (1, 2, 0))
        self.assertEqual(summary.coordinates, (0.0, 1.0))

    def test_finite_iterables_are_supported(self) -> None:
        summary = gap_simplex(iter([3.0, 2.0, 0.0]), k=3)

        self.assertEqual(summary.coordinates, (1.0 / 3.0, 2.0 / 3.0))

    def test_full_distribution_statistics_are_stable(self) -> None:
        summary = gap_simplex([10_000.0, 9_999.0, -10_000.0], k=2)

        self.assertTrue(0.0 < summary.max_probability < 1.0)
        self.assertTrue(0.0 < summary.top_k_probability_mass <= 1.0)
        self.assertGreaterEqual(summary.entropy, 0.0)

    def test_tail_bounds_contain_actual_mass(self) -> None:
        summary = gap_simplex([4.0, 2.0, 1.0, 0.5, -2.0], k=3)
        bounds = tail_mass_bounds(summary, vocabulary_size=5)

        self.assertLessEqual(bounds.top_k_mass_lower, summary.top_k_probability_mass)
        self.assertLessEqual(summary.top_k_probability_mass, bounds.top_k_mass_upper)
        self.assertLessEqual(bounds.top1_probability_lower, summary.max_probability)
        self.assertLessEqual(summary.max_probability, bounds.top1_probability_upper)

    def test_tail_lower_bounds_are_attained_by_tied_tail(self) -> None:
        summary = gap_simplex([4.0, 2.0, 1.0, 1.0, 1.0], k=3)
        bounds = tail_mass_bounds(summary, vocabulary_size=5)

        self.assertAlmostEqual(bounds.top_k_mass_lower, summary.top_k_probability_mass)
        self.assertAlmostEqual(bounds.top1_probability_lower, summary.max_probability)

    def test_nonempty_tail_approaches_but_does_not_attain_upper_bound(self) -> None:
        summary = gap_simplex([4.0, 2.0, 1.0, -20.0, -20.0], k=3)
        bounds = tail_mass_bounds(summary, vocabulary_size=5)

        self.assertLess(summary.top_k_probability_mass, bounds.top_k_mass_upper)
        self.assertLess(summary.max_probability, bounds.top1_probability_upper)
        self.assertAlmostEqual(summary.top_k_probability_mass, 1.0, places=9)
        self.assertAlmostEqual(
            summary.max_probability,
            bounds.top1_probability_upper,
            places=9,
        )

    def test_tail_bounds_are_exact_for_full_vocabulary(self) -> None:
        summary = gap_simplex([3.0, 2.0, -1.0], k=3)
        bounds = tail_mass_bounds(summary, vocabulary_size=3)

        self.assertEqual(bounds.top_k_mass_lower, 1.0)
        self.assertEqual(bounds.top_k_mass_upper, 1.0)
        self.assertAlmostEqual(bounds.top1_probability_lower, summary.max_probability)
        self.assertAlmostEqual(bounds.top1_probability_upper, summary.max_probability)

    def test_invalid_inputs_fail_loudly(self) -> None:
        invalid = (
            ([1.0], {}),
            ([1.0, float("nan")], {}),
            ([True, 1.0], {}),
            ([1.0, 0.0], {"k": 1}),
            ([1.0, 0.0], {"flat_tolerance": -1.0}),
        )
        for logits, kwargs in invalid:
            with self.subTest(logits=logits, kwargs=kwargs):
                with self.assertRaises((TypeError, ValueError)):
                    gap_simplex(logits, **kwargs)


class DiagnosticTests(unittest.TestCase):
    def test_margin_diagnostic_reports_exact_bound(self) -> None:
        diagnostic = relaxed_margin_diagnostic(
            [5.0, 4.0, 1.0, -2.0],
            1,
            k=4,
            rho=0.2,
        )

        self.assertTrue(diagnostic.accepted)
        self.assertEqual(diagnostic.rank, 2)
        self.assertAlmostEqual(diagnostic.exact_probability_ratio, math.exp(-1.0))
        self.assertIsNotNone(diagnostic.certified_ratio_lower_bound)
        self.assertGreaterEqual(
            diagnostic.exact_probability_ratio,
            diagnostic.certified_ratio_lower_bound or 0.0,
        )

    def test_margin_diagnostic_rejects_outside_top_k(self) -> None:
        diagnostic = relaxed_margin_diagnostic([5.0, 4.0, 1.0, -2.0], 3, k=2, rho=1.0)

        self.assertFalse(diagnostic.accepted)
        self.assertIn("outside", diagnostic.reason)

    def test_absolute_cap_prevents_scale_dependent_acceptance(self) -> None:
        diagnostic = relaxed_margin_diagnostic(
            [100.0, 91.0, 0.0],
            1,
            k=3,
            rho=0.10,
            absolute_margin_cap=2.0,
        )

        self.assertFalse(diagnostic.accepted)
        self.assertIn("absolute", diagnostic.reason)

    def test_margin_diagnostic_does_not_impute_flat_case(self) -> None:
        diagnostic = relaxed_margin_diagnostic([1.0, 1.0, 1.0], 0, k=3, rho=1.0)

        self.assertFalse(diagnostic.accepted)
        self.assertIsNone(diagnostic.normalized_loss)
        self.assertIn("undefined", diagnostic.reason)

    def test_heuristic_acceptance_changes_proposal_distribution(self) -> None:
        accepted = conditional_accepted_distribution([0.5, 0.5], [1.0, 1.0])

        self.assertEqual(accepted, (0.5, 0.5))
        self.assertNotEqual(accepted, (0.6, 0.4))

    def test_zero_acceptance_has_no_conditional_distribution(self) -> None:
        with self.assertRaisesRegex(ValueError, "never accepts"):
            conditional_accepted_distribution([0.5, 0.5], [0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
