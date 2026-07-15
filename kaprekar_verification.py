"""Backward-compatible supplementary verifier for the Kaprekar paper.

The production implementation lives in ``src/kaprekar``. This wrapper preserves
the original functions and script output while adding strict domain validation.
"""

from __future__ import annotations

import sys
from pathlib import Path


try:
    from kaprekar.core import (
        digits_base,
        kaprekar_map,
        kaprekar_spectrum_from_digits,
        lambda_bn,
        sigma_of_number,
    )
    from kaprekar.dynamics import decimal_fixed_spectra
    from kaprekar.verification import verify_ranges as _verify_ranges_report
except ModuleNotFoundError as error:
    if error.name != "kaprekar":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    from kaprekar.core import (  # type: ignore[no-redef]
        digits_base,
        kaprekar_map,
        kaprekar_spectrum_from_digits,
        lambda_bn,
        sigma_of_number,
    )
    from kaprekar.dynamics import decimal_fixed_spectra  # type: ignore[no-redef]
    from kaprekar.verification import (  # type: ignore[no-redef]
        verify_ranges as _verify_ranges_report,
    )


def verify_ranges(
    b_min: int = 2,
    b_max: int = 8,
    n_min: int = 1,
    n_max: int = 7,
) -> list[tuple[int, int, int, int]]:
    """Preserve the original row-oriented exhaustive verification API."""

    report = _verify_ranges_report(
        b_min,
        b_max,
        n_min,
        n_max,
        mode="exhaustive",
    )
    if not report.passed:
        failures = [failure for case in report.cases for failure in case.failures]
        raise AssertionError("; ".join(failures))
    return [
        (
            case.base,
            case.digits,
            case.observed_image_size,
            case.expected_image_size,
        )
        for case in report.cases
        if case.observed_image_size is not None
    ]


def main() -> int:
    rows = verify_ranges()
    print(
        f"Verified factorization and image-cardinality for {len(rows)} cases:"
    )
    for b, n, observed, predicted in rows:
        print(
            f"  base={b}, digits={n}, observed={observed}, predicted={predicted}"
        )

    print("\nDecimal fixed spectra for n=3..8:")
    for n in range(3, 9):
        print(f"  n={n}: {decimal_fixed_spectra(n)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "decimal_fixed_spectra",
    "digits_base",
    "kaprekar_map",
    "kaprekar_spectrum_from_digits",
    "lambda_bn",
    "main",
    "sigma_of_number",
    "verify_ranges",
]
