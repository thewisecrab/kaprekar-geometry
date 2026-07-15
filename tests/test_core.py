from __future__ import annotations

import unittest

from kaprekar.core import (
    digit_multiset_count,
    digits_base,
    enumerate_spectra,
    kaprekar_map,
    kaprekar_spectrum_from_digits,
    lambda_bn,
    number_from_digits,
    representative_from_spectrum,
    spectrum_count,
    spectrum_of_number,
    validate_spectrum,
)


class CoreArithmeticTests(unittest.TestCase):
    def test_digits_include_leading_zeroes_and_round_trip(self) -> None:
        self.assertEqual(digits_base(42, 10, 4), [0, 0, 4, 2])
        self.assertEqual(digits_base(255, 16, 2), [15, 15])
        for b in range(2, 9):
            for n in range(1, 5):
                for x in range(b**n):
                    self.assertEqual(number_from_digits(digits_base(x, b, n), b), x)

    def test_known_decimal_steps(self) -> None:
        self.assertEqual(kaprekar_map(3524, 10, 4), 3087)
        self.assertEqual(kaprekar_map(2111, 10, 4), 999)
        self.assertEqual(kaprekar_map(6174, 10, 4), 6174)
        self.assertEqual(spectrum_of_number(6174, 10, 4), (6, 2))
        self.assertEqual(lambda_bn((6, 2), 10, 4), 6174)

    def test_one_digit_domain_has_one_empty_spectrum(self) -> None:
        self.assertEqual(list(enumerate_spectra(10, 1)), [()])
        self.assertEqual(spectrum_count(10, 1), 1)
        self.assertEqual(lambda_bn((), 10, 1), 0)
        self.assertEqual(kaprekar_map(9, 10, 1), 0)

    def test_spectrum_enumeration_is_complete_and_deterministic(self) -> None:
        spectra = list(enumerate_spectra(3, 4))
        self.assertEqual(
            spectra,
            [(2, 2), (2, 1), (2, 0), (1, 1), (1, 0), (0, 0)],
        )
        self.assertEqual(len(spectra), spectrum_count(3, 4))
        self.assertEqual(spectrum_count(10, 4), 55)
        self.assertEqual(spectrum_count(10, 10), 2002)
        self.assertEqual(digit_multiset_count(10, 4), 715)

    def test_every_spectrum_has_the_proof_representative(self) -> None:
        for b in range(2, 9):
            for n in range(1, 8):
                values: set[int] = set()
                for spectrum in enumerate_spectra(b, n):
                    x = representative_from_spectrum(spectrum, b, n)
                    self.assertEqual(spectrum_of_number(x, b, n), spectrum)
                    value = lambda_bn(spectrum, b, n)
                    self.assertEqual(kaprekar_map(x, b, n), value)
                    values.add(value)
                self.assertEqual(len(values), spectrum_count(b, n))

    def test_factorization_exhaustively_on_fast_grid(self) -> None:
        for b in range(2, 6):
            for n in range(1, 6):
                for x in range(b**n):
                    self.assertEqual(
                        kaprekar_map(x, b, n),
                        lambda_bn(spectrum_of_number(x, b, n), b, n),
                    )

    def test_strict_number_validation_rejects_silent_wrapping(self) -> None:
        invalid_calls = (
            lambda: digits_base(-1, 10, 4),
            lambda: digits_base(10_000, 10, 4),
            lambda: digits_base(12.5, 10, 2),  # type: ignore[arg-type]
            lambda: digits_base(1, 1, 4),
            lambda: digits_base(1, 10, 0),
            lambda: kaprekar_map(True, 10, 4),
        )
        for call in invalid_calls:
            with self.subTest(call=call):
                with self.assertRaises((TypeError, ValueError)):
                    call()

    def test_strict_digit_and_spectrum_validation(self) -> None:
        with self.assertRaises(ValueError):
            kaprekar_spectrum_from_digits([])
        with self.assertRaises(ValueError):
            kaprekar_spectrum_from_digits([-1, 2])
        with self.assertRaises(ValueError):
            kaprekar_spectrum_from_digits([0, 10], 10)
        with self.assertRaises(TypeError):
            kaprekar_spectrum_from_digits([False, 1])

        invalid_spectra = (
            (),
            (1,),
            (1, 2),
            (10, 0),
            (-1, 0),
            (True, 0),
            (1, 1, 1),
        )
        for spectrum in invalid_spectra:
            with self.subTest(spectrum=spectrum):
                with self.assertRaises((TypeError, ValueError)):
                    validate_spectrum(spectrum, 10, 4)

    def test_malformed_lambda_cannot_produce_float(self) -> None:
        with self.assertRaises(ValueError):
            lambda_bn((1, 1, 1, 1, 1), 10, 4)


if __name__ == "__main__":
    unittest.main()
