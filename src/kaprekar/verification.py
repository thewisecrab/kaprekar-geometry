"""Guarded, structured verification for Kaprekar spectrum identities."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from random import Random
from sys import maxsize
from time import perf_counter
from typing import Iterable

from .core import (
    ComputationLimitError,
    enumerate_spectra,
    kaprekar_map,
    lambda_bn,
    representative_from_spectrum,
    require_bool,
    require_int,
    spectrum_count,
    spectrum_of_number,
    validate_base_and_digits,
)


VERIFICATION_MODES = frozenset({"exhaustive", "reduced", "sampled"})
DEFAULT_STATE_LIMIT = 5_000_000
DEFAULT_WORK_UNIT_LIMIT = 50_000_000
DEFAULT_CASE_LIMIT = 10_000
DEFAULT_DIGIT_LIMIT = 10_000
DEFAULT_SAMPLE_SIZE = 10_000
DEFAULT_SAMPLE_SEED = 0x6174


def _validate_mode(mode: object) -> str:
    if not isinstance(mode, str):
        raise TypeError(f"mode must be a string, not {type(mode).__name__}")
    if mode not in VERIFICATION_MODES:
        expected = ", ".join(sorted(VERIFICATION_MODES))
        raise ValueError(f"mode must be one of {expected}, got {mode!r}")
    return mode


def _case_seed(seed: int, b: int, n: int) -> int:
    return (seed ^ (b * 0x9E3779B185EBCA87) ^ (n * 0xC2B2AE3D27D4EB4F)) & (
        (1 << 64) - 1
    )


def _sample_without_replacement(total: int, count: int, seed: int) -> Iterable[int]:
    if count == total:
        return range(total)
    rng = Random(seed)
    if total <= maxsize:
        return rng.sample(range(total), count)
    selected: list[int] = []
    seen: set[int] = set()
    while len(selected) < count:
        candidate = rng.randrange(total)
        if candidate not in seen:
            seen.add(candidate)
            selected.append(candidate)
    return selected


@dataclass(frozen=True, slots=True)
class CaseVerification:
    """Structured evidence from one ``(base, digits)`` verification case."""

    base: int
    digits: int
    mode: str
    passed: bool
    total_raw_states: int
    total_spectra: int
    states_checked: int
    factorization_checks: int
    factorization_scope: str
    expected_image_size: int
    observed_image_size: int | None
    distinct_outputs_observed: int
    image_cardinality_verified: bool
    lambda_injective: bool | None
    sample_seed: int | None
    sample_sha256: str | None
    failures: tuple[str, ...]
    duration_seconds: float

    def to_dict(self) -> dict[str, object]:
        return {
            "base": self.base,
            "digits": self.digits,
            "mode": self.mode,
            "passed": self.passed,
            "total_raw_states": self.total_raw_states,
            "total_spectra": self.total_spectra,
            "states_checked": self.states_checked,
            "factorization_checks": self.factorization_checks,
            "factorization_scope": self.factorization_scope,
            "expected_image_size": self.expected_image_size,
            "observed_image_size": self.observed_image_size,
            "distinct_outputs_observed": self.distinct_outputs_observed,
            "image_cardinality_verified": self.image_cardinality_verified,
            "lambda_injective": self.lambda_injective,
            "sample_seed": self.sample_seed,
            "sample_sha256": self.sample_sha256,
            "failures": list(self.failures),
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True, slots=True)
class VerificationReport:
    """Aggregate, JSON-ready report over one or more verification cases."""

    mode: str
    passed: bool
    cases: tuple[CaseVerification, ...]
    total_states_checked: int
    total_factorization_checks: int
    duration_seconds: float

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "passed": self.passed,
            "case_count": len(self.cases),
            "total_states_checked": self.total_states_checked,
            "total_factorization_checks": self.total_factorization_checks,
            "duration_seconds": self.duration_seconds,
            "cases": [case.to_dict() for case in self.cases],
        }


def _planned_states(b: int, n: int, mode: str, sample_size: int) -> int:
    if mode == "exhaustive":
        return b**n
    if mode == "reduced":
        return spectrum_count(b, n)
    return min(sample_size, b**n)


def _verify_case_unchecked(
    b: int,
    n: int,
    *,
    mode: str,
    sample_size: int,
    seed: int,
) -> CaseVerification:
    started = perf_counter()
    total_raw = b**n
    total_spectra = spectrum_count(b, n)
    expected_image_size = total_spectra
    failures: list[str] = []
    factorization_checks = 0
    outputs: set[int] = set()
    observed_image_size: int | None = None
    image_cardinality_verified = False
    lambda_injective: bool | None = None
    effective_seed: int | None = None
    sample_hasher = None

    if mode == "exhaustive":
        numbers: Iterable[int] = range(total_raw)
        factorization_scope = "all_raw_states"
    elif mode == "sampled":
        effective_seed = _case_seed(seed, b, n)
        sample_hasher = sha256()
        numbers = _sample_without_replacement(
            total_raw, min(sample_size, total_raw), effective_seed
        )
        factorization_scope = "seeded_raw_sample"
    else:
        numbers = ()
        factorization_scope = "one_representative_per_spectrum"

    if mode in {"exhaustive", "sampled"}:
        for x in numbers:
            if sample_hasher is not None:
                sample_hasher.update(str(x).encode("ascii"))
                sample_hasher.update(b"\n")
            direct = kaprekar_map(x, b, n)
            factored = lambda_bn(spectrum_of_number(x, b, n), b, n)
            factorization_checks += 1
            outputs.add(direct)
            if direct != factored and len(failures) < 10:
                failures.append(
                    f"factorization failed at x={x}: direct={direct}, factored={factored}"
                )

    if mode in {"exhaustive", "reduced"}:
        reduced_outputs: list[int] = []
        for spectrum in enumerate_spectra(b, n):
            value = lambda_bn(spectrum, b, n)
            reduced_outputs.append(value)
            if mode == "reduced":
                representative = representative_from_spectrum(spectrum, b, n)
                representative_spectrum = spectrum_of_number(representative, b, n)
                direct = kaprekar_map(representative, b, n)
                factorization_checks += 1
                if representative_spectrum != spectrum and len(failures) < 10:
                    failures.append(
                        f"representative {representative} has spectrum "
                        f"{representative_spectrum}, expected {spectrum}"
                    )
                if direct != value and len(failures) < 10:
                    failures.append(
                        f"representative factorization failed for {spectrum}: "
                        f"direct={direct}, factored={value}"
                    )

        reduced_image = set(reduced_outputs)
        lambda_injective = len(reduced_image) == len(reduced_outputs)
        if not lambda_injective:
            failures.append("Lambda is not injective on the enumerated spectrum space")
        observed_image_size = (
            len(outputs) if mode == "exhaustive" else len(reduced_image)
        )
        image_cardinality_verified = observed_image_size == expected_image_size
        if not image_cardinality_verified:
            failures.append(
                f"image cardinality mismatch: observed={observed_image_size}, "
                f"expected={expected_image_size}"
            )
        if mode == "exhaustive" and outputs != reduced_image:
            failures.append("raw and reduced image sets differ")
        if mode == "reduced":
            outputs = reduced_image

    states_checked = (
        total_raw
        if mode == "exhaustive"
        else total_spectra
        if mode == "reduced"
        else factorization_checks
    )
    return CaseVerification(
        base=b,
        digits=n,
        mode=mode,
        passed=not failures,
        total_raw_states=total_raw,
        total_spectra=total_spectra,
        states_checked=states_checked,
        factorization_checks=factorization_checks,
        factorization_scope=factorization_scope,
        expected_image_size=expected_image_size,
        observed_image_size=observed_image_size,
        distinct_outputs_observed=len(outputs),
        image_cardinality_verified=image_cardinality_verified,
        lambda_injective=lambda_injective,
        sample_seed=effective_seed,
        sample_sha256=(None if sample_hasher is None else sample_hasher.hexdigest()),
        failures=tuple(failures),
        duration_seconds=round(perf_counter() - started, 6),
    )


def verify_ranges(
    b_min: int = 2,
    b_max: int = 8,
    n_min: int = 1,
    n_max: int = 7,
    *,
    mode: str = "exhaustive",
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    seed: int = DEFAULT_SAMPLE_SEED,
    max_states: int = DEFAULT_STATE_LIMIT,
    max_work_units: int = DEFAULT_WORK_UNIT_LIMIT,
    max_cases: int = DEFAULT_CASE_LIMIT,
    max_digits: int = DEFAULT_DIGIT_LIMIT,
    force: bool = False,
) -> VerificationReport:
    """Verify an inclusive rectangular grid with declared work and scope guards."""

    mode = _validate_mode(mode)
    lower_base = require_int("b_min", b_min, minimum=2)
    upper_base = require_int("b_max", b_max, minimum=2)
    lower_digits = require_int("n_min", n_min, minimum=1)
    upper_digits = require_int("n_max", n_max, minimum=1)
    sample_size = require_int("sample_size", sample_size, minimum=1)
    seed = require_int("seed", seed)
    max_states = require_int("max_states", max_states, minimum=1)
    max_work_units = require_int("max_work_units", max_work_units, minimum=1)
    max_cases = require_int("max_cases", max_cases, minimum=1)
    max_digits = require_int("max_digits", max_digits, minimum=1)
    force = require_bool("force", force)

    if lower_base > upper_base:
        raise ValueError("b_min must be <= b_max")
    if lower_digits > upper_digits:
        raise ValueError("n_min must be <= n_max")

    case_count = (upper_base - lower_base + 1) * (
        upper_digits - lower_digits + 1
    )
    if case_count > max_cases and not force:
        raise ComputationLimitError(
            f"verification grid has {case_count:,} cases, above the "
            f"{max_cases:,} case limit"
        )
    if upper_digits > max_digits and not force:
        raise ComputationLimitError(
            f"digit count {upper_digits:,} exceeds the {max_digits:,} digit limit"
        )

    configurations = tuple(
        (b, n)
        for b in range(lower_base, upper_base + 1)
        for n in range(lower_digits, upper_digits + 1)
    )
    planned = tuple(
        (_planned_states(b, n, mode, sample_size), n)
        for b, n in configurations
    )
    planned_states = sum(states for states, _ in planned)
    planned_work_units = sum(states * n for states, n in planned)
    if planned_states > max_states and not force:
        raise ComputationLimitError(
            f"{mode} verification plans {planned_states:,} states, above the "
            f"{max_states:,} state limit"
        )
    if planned_work_units > max_work_units and not force:
        raise ComputationLimitError(
            f"{mode} verification plans {planned_work_units:,} digit-state work "
            f"units, above the {max_work_units:,} limit"
        )

    started = perf_counter()
    cases = tuple(
        _verify_case_unchecked(
            b,
            n,
            mode=mode,
            sample_size=sample_size,
            seed=seed,
        )
        for b, n in configurations
    )
    return VerificationReport(
        mode=mode,
        passed=all(case.passed for case in cases),
        cases=cases,
        total_states_checked=sum(case.states_checked for case in cases),
        total_factorization_checks=sum(
            case.factorization_checks for case in cases
        ),
        duration_seconds=round(perf_counter() - started, 6),
    )


def verify_case(
    b: int,
    n: int,
    **kwargs: object,
) -> CaseVerification:
    """Convenience wrapper returning the sole case from :func:`verify_ranges`."""

    base, digit_count = validate_base_and_digits(b, n)
    report = verify_ranges(
        base,
        base,
        digit_count,
        digit_count,
        **kwargs,
    )
    return report.cases[0]


__all__ = [
    "CaseVerification",
    "DEFAULT_CASE_LIMIT",
    "DEFAULT_DIGIT_LIMIT",
    "DEFAULT_SAMPLE_SEED",
    "DEFAULT_SAMPLE_SIZE",
    "DEFAULT_STATE_LIMIT",
    "DEFAULT_WORK_UNIT_LIMIT",
    "VERIFICATION_MODES",
    "VerificationReport",
    "verify_case",
    "verify_ranges",
]
