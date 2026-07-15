from __future__ import annotations

from fractions import Fraction
from math import comb
from random import Random
import unittest

from kaprekar import kaprekar_map, lambda_bn, spectrum_of_number
from kaprekar.selective import clopper_pearson_upper


class UniversalIdentityStressTests(unittest.TestCase):
    def test_coefficient_dominance_identity_on_wide_grid(self) -> None:
        for base in range(2, 51):
            for digits in range(1, 101):
                half = digits // 2
                coefficients = tuple(
                    base ** (digits - index) - base ** (index - 1)
                    for index in range(1, half + 1)
                )
                for index, coefficient in enumerate(coefficients, start=1):
                    direct_margin = coefficient - (base - 1) * sum(
                        coefficients[index:]
                    )
                    closed_form = (
                        base ** (digits - half)
                        + base**half
                        - base**index
                        - base ** (index - 1)
                    )
                    self.assertEqual(direct_margin, closed_form)
                    self.assertGreater(direct_margin, 0)

    def test_factorization_on_seeded_large_parameter_cases(self) -> None:
        random = Random(0xC0FFEE6174)
        for _ in range(5_000):
            base = random.randint(2, 64)
            digits = random.randint(1, 40)
            value = random.randrange(base**digits)
            spectrum = spectrum_of_number(value, base, digits)
            self.assertEqual(
                kaprekar_map(value, base, digits),
                lambda_bn(spectrum, base, digits),
            )

    def test_normalized_gap_reconstruction_is_exact_over_rationals(self) -> None:
        random = Random(0x495)
        for width in range(2, 20):
            for _ in range(50):
                gaps = tuple(
                    Fraction(random.randint(0, 20), random.randint(1, 20))
                    for _ in range(width - 1)
                )
                if not any(gaps):
                    gaps = (Fraction(1),) + gaps[1:]
                bottom = Fraction(random.randint(-10, 10), 3)
                values = [bottom]
                for gap in reversed(gaps):
                    values.append(values[-1] + gap)
                sorted_values = tuple(reversed(values))
                spread = sorted_values[0] - sorted_values[-1]
                coordinates = tuple(gap / spread for gap in gaps)

                self.assertEqual(sum(coordinates), 1)
                for index in range(width):
                    reconstructed = spread * sum(coordinates[index:])
                    self.assertEqual(
                        reconstructed,
                        sorted_values[index] - sorted_values[-1],
                    )

    def test_exact_speculative_residual_identity_over_rationals(self) -> None:
        random = Random(0xBEEF)
        for outcomes in range(2, 20):
            for _ in range(100):
                p_weights = [random.randint(1, 100) for _ in range(outcomes)]
                q_weights = [random.randint(1, 100) for _ in range(outcomes)]
                p_total = sum(p_weights)
                q_total = sum(q_weights)
                target = tuple(Fraction(weight, p_total) for weight in p_weights)
                proposal = tuple(Fraction(weight, q_total) for weight in q_weights)
                acceptance = tuple(
                    min(Fraction(1), p / q)
                    for p, q in zip(target, proposal, strict=True)
                )
                accepted_mass = tuple(
                    q * a
                    for q, a in zip(proposal, acceptance, strict=True)
                )
                rejection = 1 - sum(accepted_mass)
                if rejection == 0:
                    self.assertEqual(accepted_mass, target)
                    continue
                residual = tuple(
                    (p - accepted) / rejection
                    for p, accepted in zip(
                        target,
                        accepted_mass,
                        strict=True,
                    )
                )
                self.assertTrue(all(value >= 0 for value in residual))
                self.assertEqual(sum(residual), 1)
                final = tuple(
                    accepted + rejection * replacement
                    for accepted, replacement in zip(
                        accepted_mass,
                        residual,
                        strict=True,
                    )
                )
                self.assertEqual(final, target)

    def test_maximal_acceptance_equals_one_minus_total_variation(self) -> None:
        examples = (
            ((Fraction(1, 2), Fraction(1, 2)), (Fraction(3, 5), Fraction(2, 5))),
            ((Fraction(1), Fraction(0)), (Fraction(0), Fraction(1))),
            (
                (Fraction(0), Fraction(1, 3), Fraction(2, 3)),
                (Fraction(1, 4), Fraction(0), Fraction(3, 4)),
            ),
        )
        for target, proposal in examples:
            accepted = sum(min(p, q) for p, q in zip(target, proposal, strict=True))
            total_variation = Fraction(1, 2) * sum(
                abs(p - q) for p, q in zip(target, proposal, strict=True)
            )
            self.assertEqual(accepted, 1 - total_variation)

    def test_zero_rejection_requires_proposal_to_equal_target(self) -> None:
        proposal = (Fraction(1, 3), Fraction(2, 3))
        full_acceptance = (Fraction(1), Fraction(1))
        accepted = tuple(
            q * a for q, a in zip(proposal, full_acceptance, strict=True)
        )

        self.assertEqual(1 - sum(accepted), 0)
        self.assertEqual(accepted, proposal)
        self.assertNotEqual(accepted, (Fraction(1, 2), Fraction(1, 2)))

    def test_zero_rejection_exact_case_and_null_acceptance_irrelevance(self) -> None:
        target = proposal = (Fraction(0), Fraction(1, 3), Fraction(2, 3))
        first_acceptance = (Fraction(0), Fraction(1), Fraction(1))
        second_acceptance = (Fraction(1), Fraction(1), Fraction(1))

        first_mass = tuple(
            q * a for q, a in zip(proposal, first_acceptance, strict=True)
        )
        second_mass = tuple(
            q * a for q, a in zip(proposal, second_acceptance, strict=True)
        )
        self.assertEqual(first_mass, target)
        self.assertEqual(second_mass, target)
        self.assertEqual(1 - sum(first_mass), 0)

    def test_feasible_nonmaximal_acceptance_has_exact_residual(self) -> None:
        target = (Fraction(3, 5), Fraction(2, 5))
        proposal = (Fraction(1, 2), Fraction(1, 2))
        acceptance = (Fraction(1, 2), Fraction(1, 2))
        accepted = tuple(
            q * a for q, a in zip(proposal, acceptance, strict=True)
        )
        rejection = 1 - sum(accepted)
        residual = tuple(
            (p - mass) / rejection
            for p, mass in zip(target, accepted, strict=True)
        )
        reconstructed = tuple(
            mass + rejection * replacement
            for mass, replacement in zip(accepted, residual, strict=True)
        )

        self.assertEqual(sum(accepted), Fraction(1, 2))
        self.assertEqual(residual, (Fraction(7, 10), Fraction(3, 10)))
        self.assertEqual(reconstructed, target)
        self.assertLess(
            sum(accepted),
            sum(min(p, q) for p, q in zip(target, proposal, strict=True)),
        )


class SelectiveRiskProofTests(unittest.TestCase):
    def test_clopper_pearson_has_one_sided_binomial_coverage(self) -> None:
        alpha = 0.05
        for trials in range(1, 31):
            upper_bounds = tuple(
                clopper_pearson_upper(errors, trials, alpha=alpha)
                for errors in range(trials + 1)
            )
            for numerator in range(1, 100):
                probability = numerator / 100
                failure_probability = sum(
                    comb(trials, errors)
                    * probability**errors
                    * (1.0 - probability) ** (trials - errors)
                    for errors, bound in enumerate(upper_bounds)
                    if bound < probability
                )
                self.assertLessEqual(
                    failure_probability,
                    alpha + 1e-12,
                    (trials, probability, failure_probability),
                )


if __name__ == "__main__":
    unittest.main()
