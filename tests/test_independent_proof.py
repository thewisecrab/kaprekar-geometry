from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kaprekar.core import (
    enumerate_spectra,
    kaprekar_map,
    lambda_bn,
    spectrum_of_number,
)
from kaprekar.dynamics import analyze_functional_graph, raw_spectrum_weights, reduced_map
from proofs.independent_oracle import (
    build_certificate,
    brute_raw_graph,
    coefficient_closed_form_slacks,
    coefficient_slacks,
    direct_kaprekar,
    exhaustive_case_proof,
    graph_proof,
    linear_image,
    recompute_and_verify_certificate,
    reduced_successor,
    spectra,
    spectrum,
    spectrum_weights,
    structural_proof,
    verify_certificate_envelope,
)


ARTIFACT = ROOT / "results" / "independent_proof_certificate.json"


class IndependentOracleTests(unittest.TestCase):
    def test_raw_arithmetic_agrees_without_importing_production_logic(self) -> None:
        for base in range(2, 6):
            for digits in range(1, 6):
                for value in range(base**digits):
                    with self.subTest(base=base, digits=digits, value=value):
                        self.assertEqual(
                            direct_kaprekar(value, base, digits),
                            kaprekar_map(value, base, digits),
                        )
                        self.assertEqual(
                            spectrum(value, base, digits),
                            spectrum_of_number(value, base, digits),
                        )

    def test_structural_kernel_across_arbitrary_bases_and_widths(self) -> None:
        # This deliberately reaches beyond the paper's base-2..8 test grid.
        for base in range(2, 13):
            for digits in range(1, 11):
                proof = structural_proof(base, digits)
                with self.subTest(base=base, digits=digits):
                    self.assertTrue(all(proof["checks"].values()))
                    slacks = coefficient_slacks(base, digits)
                    self.assertEqual(slacks, coefficient_closed_form_slacks(base, digits))
                    self.assertTrue(all(slack > 0 for slack in slacks))
                    self.assertEqual(spectra(base, digits), tuple(enumerate_spectra(base, digits)))

    def test_reduced_maps_and_linear_images_cross_check(self) -> None:
        for base in range(2, 9):
            for digits in range(1, 8):
                for state in spectra(base, digits):
                    with self.subTest(base=base, digits=digits, state=state):
                        self.assertEqual(
                            linear_image(state, base, digits),
                            lambda_bn(state, base, digits),
                        )
                        self.assertEqual(
                            reduced_successor(state, base, digits),
                            reduced_map(state, base, digits),
                        )

    def test_independent_weights_match_production_and_brute_force(self) -> None:
        for base in range(2, 6):
            for digits in range(1, 6):
                independent = spectrum_weights(base, digits)
                brute = Counter(
                    spectrum(value, base, digits) for value in range(base**digits)
                )
                with self.subTest(base=base, digits=digits):
                    self.assertEqual(independent, dict(brute))
                    self.assertEqual(independent, raw_spectrum_weights(base, digits))

    def test_graph_cycles_basins_depths_and_indegrees_cross_check(self) -> None:
        for base in range(2, 6):
            for digits in range(1, 6):
                independent = exhaustive_case_proof(base, digits)
                production = analyze_functional_graph(base, digits)
                independent_cycles = {
                    tuple(cycle["numeric_cycle"]): (
                        cycle["raw_basin_size"],
                        cycle["maximum_reduced_depth"],
                    )
                    for cycle in independent["cycles"]
                }
                production_cycles = {
                    attractor.cycle_values: (
                        attractor.raw_basin_size,
                        attractor.maximum_reduced_depth,
                    )
                    for attractor in production.attractors
                }
                with self.subTest(base=base, digits=digits):
                    self.assertEqual(independent_cycles, production_cycles)
                    self.assertEqual(
                        independent["raw_hitting_histogram"],
                        {
                            str(step): count
                            for step, count in production.raw_convergence_histogram
                        },
                    )

    def test_weighted_reduction_matches_independent_direct_raw_graph(self) -> None:
        # This validates the graph/basin theorem without consulting production
        # graph logic: one side sees only K on raw integers, while the other is
        # reconstructed from spectra and exact fiber weights.
        for base in range(2, 6):
            for digits in range(1, 6):
                direct = brute_raw_graph(base, digits)
                weights = spectrum_weights(base, digits)
                reduced = graph_proof(base, digits, weights)
                reduced_basins = {
                    min(
                        numeric_cycle[index:] + numeric_cycle[:index]
                        for index in range(len(cycle))
                    ): reduced.raw_basin_sizes[cycle]
                    for cycle in reduced.cycles
                    for numeric_cycle in (
                        tuple(linear_image(state, base, digits) for state in cycle),
                    )
                }
                with self.subTest(base=base, digits=digits):
                    self.assertEqual(direct.raw_basin_sizes, reduced_basins)
                    self.assertEqual(
                        direct.raw_hitting_histogram,
                        reduced.raw_hitting_histogram,
                    )
                    for state, weight in weights.items():
                        self.assertEqual(
                            direct.raw_indegrees[linear_image(state, base, digits)],
                            weight,
                        )

    def test_decimal_widths_five_through_eight_match_independent_graph(self) -> None:
        def canonical_numeric(cycle: tuple[int, ...]) -> tuple[int, ...]:
            return min(
                cycle[index:] + cycle[:index] for index in range(len(cycle))
            )

        for digits in range(5, 9):
            weights = spectrum_weights(10, digits)
            independent = graph_proof(10, digits, weights)
            production = analyze_functional_graph(10, digits)
            independent_basins = {
                canonical_numeric(
                    tuple(linear_image(state, 10, digits) for state in cycle)
                ): size
                for cycle, size in independent.raw_basin_sizes.items()
            }
            production_basins = {
                canonical_numeric(attractor.cycle_values): attractor.raw_basin_size
                for attractor in production.attractors
            }
            with self.subTest(digits=digits):
                self.assertEqual(weights, raw_spectrum_weights(10, digits))
                self.assertEqual(independent_basins, production_basins)
                self.assertEqual(
                    independent.raw_hitting_histogram,
                    dict(production.raw_convergence_histogram),
                )


class ProofCertificateTests(unittest.TestCase):
    def test_small_certificate_is_deterministic_and_tamper_evident(self) -> None:
        first = build_certificate(base_min=2, base_max=4, digits_min=1, digits_max=4)
        second = build_certificate(base_min=2, base_max=4, digits_min=1, digits_max=4)
        self.assertEqual(first, second)
        verify_certificate_envelope(first)

        tampered = json.loads(json.dumps(first))
        tampered["cases"][0]["raw_states_checked"] += 1
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_certificate_envelope(tampered)

    def test_checked_in_certificate_envelope(self) -> None:
        self.assertTrue(ARTIFACT.is_file(), "run scripts/prove.py --write first")
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        verify_certificate_envelope(payload)
        self.assertEqual(payload["scope"]["case_count"], 49)
        self.assertEqual(payload["scope"]["raw_states_checked"], 3_816_497)

    @unittest.skipUnless(
        os.environ.get("KAPREKAR_RUN_SLOW_TESTS") == "1",
        "set KAPREKAR_RUN_SLOW_TESTS=1 to recompute the full proof certificate",
    )
    def test_recompute_full_checked_in_certificate(self) -> None:
        payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        recompute_and_verify_certificate(payload)


if __name__ == "__main__":
    unittest.main()
