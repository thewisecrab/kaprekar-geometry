"""Validated, dependency-free arithmetic for generalized Kaprekar maps."""

from __future__ import annotations

from itertools import combinations_with_replacement
from math import comb
from typing import Iterator, Sequence, TypeAlias


Spectrum: TypeAlias = tuple[int, ...]


class ComputationLimitError(RuntimeError):
    """Raised before a requested exact computation exceeds its declared budget."""


def require_int(name: str, value: object, *, minimum: int | None = None) -> int:
    """Return ``value`` as an int after strict validation (booleans are rejected)."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer, not {type(value).__name__}")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}")
    return value


def require_bool(name: str, value: object) -> bool:
    """Return ``value`` after requiring an actual bool rather than a truthy value."""

    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool, not {type(value).__name__}")
    return value


def validate_base_and_digits(b: object, n: object) -> tuple[int, int]:
    """Validate the mathematical domain ``b >= 2`` and ``n >= 1``."""

    return require_int("b", b, minimum=2), require_int("n", n, minimum=1)


def validate_number(x: object, b: object, n: object) -> tuple[int, int, int]:
    """Validate an n-digit base-b state, where leading zeroes are significant."""

    base, digit_count = validate_base_and_digits(b, n)
    number = require_int("x", x, minimum=0)
    upper_bound = base**digit_count
    if number >= upper_bound:
        raise ValueError(
            f"x must satisfy 0 <= x < b**n ({upper_bound}), got {number}"
        )
    return number, base, digit_count


def _validated_digit_tuple(ds: Sequence[int], b: int | None = None) -> tuple[int, ...]:
    if isinstance(ds, (str, bytes, bytearray)) or not isinstance(ds, Sequence):
        raise TypeError("ds must be a finite sequence of integer digits")
    digits = tuple(ds)
    if not digits:
        raise ValueError("ds must contain at least one digit")
    if b is not None:
        base = require_int("b", b, minimum=2)
    else:
        base = None
    for index, digit in enumerate(digits):
        require_int(f"ds[{index}]", digit, minimum=0)
        if base is not None and digit >= base:
            raise ValueError(
                f"ds[{index}] must satisfy 0 <= digit < b ({base}), got {digit}"
            )
    return digits


def validate_spectrum(delta: Sequence[int], b: object, n: object) -> Spectrum:
    """Validate membership in the ordered spectrum state space S_(b,n)."""

    base, digit_count = validate_base_and_digits(b, n)
    if isinstance(delta, (str, bytes, bytearray)) or not isinstance(delta, Sequence):
        raise TypeError("delta must be a finite sequence of integer gaps")
    spectrum = tuple(delta)
    expected = digit_count // 2
    if len(spectrum) != expected:
        raise ValueError(
            f"delta must have floor(n/2)={expected} entries, got {len(spectrum)}"
        )
    previous = base
    for index, gap in enumerate(spectrum):
        require_int(f"delta[{index}]", gap, minimum=0)
        if gap >= base:
            raise ValueError(
                f"delta[{index}] must satisfy 0 <= gap < b ({base}), got {gap}"
            )
        if gap > previous:
            raise ValueError("delta must be weakly decreasing")
        previous = gap
    return spectrum


def _digits_base_unchecked(x: int, b: int, n: int) -> list[int]:
    digits = [0] * n
    for index in range(n - 1, -1, -1):
        digits[index] = x % b
        x //= b
    return digits


def _number_from_digits_unchecked(ds: Sequence[int], b: int) -> int:
    value = 0
    for digit in ds:
        value = value * b + digit
    return value


def _spectrum_from_digits_unchecked(ds: Sequence[int]) -> Spectrum:
    sorted_digits = sorted(ds, reverse=True)
    half = len(sorted_digits) // 2
    return tuple(
        sorted_digits[index] - sorted_digits[-1 - index]
        for index in range(half)
    )


def _lambda_bn_unchecked(delta: Sequence[int], b: int, n: int) -> int:
    return sum(
        (b ** (n - index - 1) - b**index) * gap
        for index, gap in enumerate(delta)
    )


def _kaprekar_map_unchecked(x: int, b: int, n: int) -> int:
    sorted_digits = sorted(_digits_base_unchecked(x, b, n), reverse=True)
    return _number_from_digits_unchecked(
        sorted_digits, b
    ) - _number_from_digits_unchecked(tuple(reversed(sorted_digits)), b)


def digits_base(x: int, b: int, n: int) -> list[int]:
    """Return the unique length-n base-b representation of x, including leading zeroes."""

    number, base, digit_count = validate_number(x, b, n)
    return _digits_base_unchecked(number, base, digit_count)


def number_from_digits(ds: Sequence[int], b: int) -> int:
    """Convert a non-empty base-b digit sequence to an integer."""

    base = require_int("b", b, minimum=2)
    digits = _validated_digit_tuple(ds, base)
    return _number_from_digits_unchecked(digits, base)


def kaprekar_spectrum_from_digits(
    ds: Sequence[int], b: int | None = None
) -> Spectrum:
    """Return the ordered outer-pair gaps of a digit sequence.

    Pass ``b`` when digit upper-bound validation is required. Without it, digits are
    still required to be non-negative integers, because the gaps themselves are
    meaningful independently of a chosen base.
    """

    return _spectrum_from_digits_unchecked(_validated_digit_tuple(ds, b))


def spectrum_of_number(x: int, b: int, n: int) -> Spectrum:
    """Return Sigma_(b,n)(x)."""

    number, base, digit_count = validate_number(x, b, n)
    return _spectrum_from_digits_unchecked(
        _digits_base_unchecked(number, base, digit_count)
    )


def sigma_of_number(y: int, b: int, n: int) -> Spectrum:
    """Backward-compatible name for :func:`spectrum_of_number`."""

    return spectrum_of_number(y, b, n)


def lambda_bn(delta: Sequence[int], b: int, n: int) -> int:
    """Evaluate the exact gap-spectral linear form Lambda_(b,n)."""

    spectrum = validate_spectrum(delta, b, n)
    base, digit_count = validate_base_and_digits(b, n)
    return _lambda_bn_unchecked(spectrum, base, digit_count)


def kaprekar_map(x: int, b: int, n: int) -> int:
    """Apply one descending-minus-ascending Kaprekar step."""

    number, base, digit_count = validate_number(x, b, n)
    return _kaprekar_map_unchecked(number, base, digit_count)


def spectrum_count(b: int, n: int) -> int:
    """Return the exact size of S_(b,n), equivalently |Im(K_(b,n))|."""

    base, digit_count = validate_base_and_digits(b, n)
    half = digit_count // 2
    return comb(base + half - 1, half)


def digit_multiset_count(b: int, n: int) -> int:
    """Return the number of sorted base-b length-n digit multisets."""

    base, digit_count = validate_base_and_digits(b, n)
    return comb(base + digit_count - 1, digit_count)


def enumerate_spectra(b: int, n: int) -> Iterator[Spectrum]:
    """Enumerate S_(b,n) exactly in deterministic descending lexicographic order."""

    base, digit_count = validate_base_and_digits(b, n)
    return combinations_with_replacement(
        range(base - 1, -1, -1), digit_count // 2
    )


def representative_from_spectrum(delta: Sequence[int], b: int, n: int) -> int:
    """Construct the proof's canonical raw state having spectrum ``delta``."""

    spectrum = validate_spectrum(delta, b, n)
    _, digit_count = validate_base_and_digits(b, n)
    return number_from_digits(spectrum + (0,) * (digit_count - len(spectrum)), b)


__all__ = [
    "ComputationLimitError",
    "Spectrum",
    "digit_multiset_count",
    "digits_base",
    "enumerate_spectra",
    "kaprekar_map",
    "kaprekar_spectrum_from_digits",
    "lambda_bn",
    "number_from_digits",
    "representative_from_spectrum",
    "require_bool",
    "require_int",
    "sigma_of_number",
    "spectrum_count",
    "spectrum_of_number",
    "validate_base_and_digits",
    "validate_number",
    "validate_spectrum",
]
