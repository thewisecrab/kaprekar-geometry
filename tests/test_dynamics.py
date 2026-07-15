from __future__ import annotations

from collections import Counter
from math import isfinite, log2
import unittest

from kaprekar.core import ComputationLimitError, kaprekar_map, spectrum_of_number
from kaprekar.dynamics import (
    analyze_functional_graph,
    fixed_spectra,
    raw_spectrum_weights,
    reduced_map,
    uniform_entropy_trajectory,
)


class DynamicsTests(unittest.TestCase):
    def test_reduced_map_and_decimal_fixed_spectra(self) -> None:
        self.assertEqual(reduced_map((6, 2), 10, 4), (6, 2))
        expected = {
            3: [((5,), 495)],
            4: [((6, 2), 6174)],
            5: [],
            6: [((6, 3, 2), 631764), ((5, 5, 0), 549945)],
            7: [],
            8: [((9, 7, 5, 1), 97508421), ((6, 3, 3, 2), 63317664)],
        }
        for n, points in expected.items():
            with self.subTest(n=n):
                self.assertEqual(fixed_spectra(10, n), points)

    def test_fixed_spectra_generalizes_base_and_zero_policy(self) -> None:
        self.assertNotIn(((), 0), fixed_spectra(10, 1))
        self.assertEqual(fixed_spectra(10, 1, include_zero=True), [((), 0)])
        for b in range(2, 7):
            for n in range(1, 6):
                for spectrum, value in fixed_spectra(b, n, include_zero=True):
                    self.assertEqual(kaprekar_map(value, b, n), value)
                    self.assertEqual(spectrum_of_number(value, b, n), spectrum)

    def test_raw_spectrum_weights_match_direct_enumeration(self) -> None:
        for b in range(2, 6):
            for n in range(1, 6):
                direct = Counter(
                    spectrum_of_number(x, b, n) for x in range(b**n)
                )
                aggregated = raw_spectrum_weights(b, n)
                with self.subTest(b=b, n=n):
                    self.assertEqual(aggregated, dict(direct))
                    self.assertEqual(sum(aggregated.values()), b**n)

    def test_two_digit_decimal_nonzero_cycle(self) -> None:
        analysis = analyze_functional_graph(10, 2)
        cycles = {attractor.cycle_values for attractor in analysis.attractors}
        self.assertIn((0,), cycles)
        nonzero = next(cycle for cycle in cycles if cycle != (0,))
        self.assertEqual(set(nonzero), {9, 81, 63, 27, 45})
        self.assertEqual(len(nonzero), 5)

    def test_small_weighted_graphs_match_raw_iteration(self) -> None:
        for b in range(2, 5):
            for n in range(1, 5):
                analysis = analyze_functional_graph(b, n)
                cycle_sets = {
                    attractor.attractor_id: set(attractor.cycle_values)
                    for attractor in analysis.attractors
                }
                basins: Counter[int] = Counter()
                histogram: Counter[int] = Counter()
                for x in range(b**n):
                    current = x
                    steps = 0
                    while not any(
                        current in cycle for cycle in cycle_sets.values()
                    ):
                        current = kaprekar_map(current, b, n)
                        steps += 1
                    attractor_id = next(
                        attractor_id
                        for attractor_id, cycle in cycle_sets.items()
                        if current in cycle
                    )
                    basins[attractor_id] += 1
                    histogram[steps] += 1
                with self.subTest(b=b, n=n):
                    self.assertEqual(
                        basins,
                        Counter(
                            {
                                attractor.attractor_id: attractor.raw_basin_size
                                for attractor in analysis.attractors
                            }
                        ),
                    )
                    self.assertEqual(
                        histogram,
                        Counter(dict(analysis.raw_convergence_histogram)),
                    )

    def test_four_digit_decimal_basins_and_histogram_are_exact(self) -> None:
        analysis = analyze_functional_graph(10, 4)
        by_cycle = {
            attractor.cycle_values: attractor for attractor in analysis.attractors
        }
        self.assertEqual(set(by_cycle), {(0,), (6174,)})
        self.assertEqual(by_cycle[(0,)].raw_basin_size, 10)
        self.assertEqual(by_cycle[(6174,)].raw_basin_size, 9990)
        self.assertEqual(sum(dict(analysis.raw_convergence_histogram).values()), 10**4)
        self.assertEqual(max(dict(analysis.raw_convergence_histogram)), 7)

        cycle_sets = [set(cycle) for cycle in by_cycle]
        brute_basins: Counter[tuple[int, ...]] = Counter()
        brute_histogram: Counter[int] = Counter()
        for x in range(10**4):
            current = x
            steps = 0
            while not any(current in cycle for cycle in cycle_sets):
                current = kaprekar_map(current, 10, 4)
                steps += 1
            cycle = next(cycle for cycle in by_cycle if current in cycle)
            brute_basins[cycle] += 1
            brute_histogram[steps] += 1

        self.assertEqual(
            brute_basins,
            Counter(
                {
                    cycle: attractor.raw_basin_size
                    for cycle, attractor in by_cycle.items()
                }
            ),
        )
        self.assertEqual(brute_histogram, Counter(dict(analysis.raw_convergence_histogram)))

    def test_full_graph_leaf_counts_and_certificate_are_exact(self) -> None:
        analysis = analyze_functional_graph(10, 4)

        self.assertEqual(len(analysis.graph_sha256), 64)
        self.assertEqual(
            analysis.graph_sha256,
            analyze_functional_graph(10, 4).graph_sha256,
        )
        self.assertEqual(
            sum(state.reduced_indegree for state in analysis.states),
            analysis.spectrum_state_count,
        )
        self.assertEqual(
            sum(state.raw_indegree or 0 for state in analysis.states),
            analysis.raw_state_count,
        )
        self.assertEqual(
            sum(state.attached_leaf_count or 0 for state in analysis.states),
            analysis.raw_state_count - analysis.spectrum_state_count,
        )

    def test_uniform_entropy_funnel_is_exact_and_nonincreasing(self) -> None:
        analysis = analyze_functional_graph(10, 4)
        trajectory = uniform_entropy_trajectory(analysis)

        self.assertAlmostEqual(trajectory[0].entropy_bits, log2(10**4))
        self.assertEqual(trajectory[0].support_size, 10**4)
        self.assertEqual(trajectory[1].support_size, 55)
        self.assertEqual(trajectory[-1].support_size, 2)
        for earlier, later in zip(trajectory, trajectory[1:]):
            self.assertLessEqual(later.entropy_bits, earlier.entropy_bits + 1e-12)
            self.assertLessEqual(later.support_size, earlier.support_size)

    def test_entropy_handles_extreme_exact_integer_ranges(self) -> None:
        analysis = analyze_functional_graph(2, 1100)
        trajectory = uniform_entropy_trajectory(
            analysis,
            through_iteration=1,
        )

        self.assertEqual(len(trajectory), 2)
        self.assertTrue(isfinite(trajectory[1].entropy_bits))
        self.assertGreaterEqual(trajectory[1].entropy_bits, 0.0)

    def test_unweighted_graph_remains_complete(self) -> None:
        analysis = analyze_functional_graph(10, 4, include_raw_weights=False)
        self.assertFalse(analysis.raw_weights_included)
        self.assertIsNone(analysis.raw_convergence_histogram)
        self.assertEqual(len(analysis.states), analysis.spectrum_state_count)
        self.assertTrue(all(state.raw_weight is None for state in analysis.states))
        self.assertTrue(
            all(attractor.raw_basin_size is None for attractor in analysis.attractors)
        )

    def test_exact_computations_enforce_declared_limits(self) -> None:
        with self.assertRaises(ComputationLimitError):
            raw_spectrum_weights(10, 8, max_multisets=100)
        with self.assertRaises(ComputationLimitError):
            fixed_spectra(10, 8, max_spectra=100)
        with self.assertRaises(ComputationLimitError):
            analyze_functional_graph(10, 8, max_spectra=100)
        with self.assertRaises(ComputationLimitError):
            analyze_functional_graph(2, 100_000)
        with self.assertRaises(ComputationLimitError):
            raw_spectrum_weights(2, 100_000)


if __name__ == "__main__":
    unittest.main()
