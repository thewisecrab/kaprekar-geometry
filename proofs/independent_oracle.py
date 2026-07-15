"""Independent exact oracle and deterministic proof certificates.

The implementation in this file deliberately shares no imports with
``src/kaprekar``.  It uses digit histograms instead of sorting for the direct
map, recursive enumeration instead of ``combinations_with_replacement``, and
independent multinomial and orbit routines.  Agreement between this module and
the production package is therefore a cross-implementation check, not a call
back into the code under test.

All arithmetic is integral.  A certificate is deterministic: it contains no
clock, platform, timing, or random fields, and its top-level SHA-256 commits to
the canonical JSON representation of every claim below it.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from math import comb
from typing import Iterable, Iterator, Mapping, Sequence
import json


Spectrum = tuple[int, ...]
Cycle = tuple[Spectrum, ...]
CERTIFICATE_SCHEMA = "kaprekar-independent-proof-v1"


def _require_domain(base: int, digits: int) -> None:
    if isinstance(base, bool) or not isinstance(base, int) or base < 2:
        raise ValueError("base must be an integer >= 2")
    if isinstance(digits, bool) or not isinstance(digits, int) or digits < 1:
        raise ValueError("digits must be an integer >= 1")


def radix_vector(value: int, base: int, digits: int) -> tuple[int, ...]:
    """Return exactly ``digits`` radix digits, including leading zeroes."""

    _require_domain(base, digits)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("value must be an integer")
    if not 0 <= value < base**digits:
        raise ValueError("value is outside the fixed-width domain")
    little_endian: list[int] = []
    remainder = value
    for _ in range(digits):
        remainder, digit = divmod(remainder, base)
        little_endian.append(digit)
    return tuple(reversed(little_endian))


def positional_value(digit_vector: Sequence[int], base: int) -> int:
    """Evaluate a radix digit vector using an explicit positional dot product."""

    value = 0
    width = len(digit_vector)
    for index, digit in enumerate(digit_vector):
        value += digit * base ** (width - index - 1)
    return value


def digit_histogram(value: int, base: int, digits: int) -> tuple[int, ...]:
    counts = [0] * base
    for digit in radix_vector(value, base, digits):
        counts[digit] += 1
    return tuple(counts)


def _ordered_digits_from_counts(
    counts: Sequence[int], *, descending: bool
) -> Iterator[int]:
    alphabet: Iterable[int]
    if descending:
        alphabet = range(len(counts) - 1, -1, -1)
    else:
        alphabet = range(len(counts))
    for digit in alphabet:
        for _ in range(counts[digit]):
            yield digit


def direct_kaprekar(value: int, base: int, digits: int) -> int:
    """Independent direct definition using a digit histogram, not sorting."""

    counts = digit_histogram(value, base, digits)
    high = positional_value(tuple(_ordered_digits_from_counts(counts, descending=True)), base)
    low = positional_value(tuple(_ordered_digits_from_counts(counts, descending=False)), base)
    return high - low


def spectrum(value: int, base: int, digits: int) -> Spectrum:
    """Return outer-pair gaps from the histogram-expanded ordered digits."""

    counts = digit_histogram(value, base, digits)
    ordered = tuple(_ordered_digits_from_counts(counts, descending=True))
    return tuple(
        ordered[index] - ordered[-index - 1] for index in range(digits // 2)
    )


def linear_image(delta: Sequence[int], base: int, digits: int) -> int:
    """Evaluate the theorem's paired positional coefficients directly."""

    _require_domain(base, digits)
    expected = digits // 2
    gaps = tuple(delta)
    if len(gaps) != expected:
        raise ValueError("spectrum has the wrong length")
    if any(
        isinstance(gap, bool)
        or not isinstance(gap, int)
        or gap < 0
        or gap >= base
        for gap in gaps
    ):
        raise ValueError("spectrum entries must be radix-sized integers")
    if any(left < right for left, right in zip(gaps, gaps[1:])):
        raise ValueError("spectrum must be weakly decreasing")
    return sum(
        gap * (base ** (digits - index) - base ** (index - 1))
        for index, gap in enumerate(gaps, start=1)
    )


def spectra(base: int, digits: int) -> tuple[Spectrum, ...]:
    """Recursively enumerate spectra in deterministic descending order."""

    _require_domain(base, digits)
    width = digits // 2
    output: list[Spectrum] = []

    def extend(prefix: Spectrum, ceiling: int) -> None:
        if len(prefix) == width:
            output.append(prefix)
            return
        for gap in range(ceiling, -1, -1):
            extend(prefix + (gap,), gap)

    extend((), base - 1)
    return tuple(output)


def representative(delta: Sequence[int], base: int, digits: int) -> int:
    """Construct a raw witness for a spectrum without calling production code."""

    gaps = tuple(delta)
    linear_image(gaps, base, digits)  # validates the spectrum
    return positional_value(gaps + (0,) * (digits - len(gaps)), base)


def reduced_successor(delta: Sequence[int], base: int, digits: int) -> Spectrum:
    return spectrum(linear_image(delta, base, digits), base, digits)


def coefficient_slacks(base: int, digits: int) -> tuple[int, ...]:
    """Return every exact superincreasing dominance slack.

    A strictly positive result proves injectivity of the linear code on the
    entire digit cube, which is stronger than injectivity only on spectra.
    """

    _require_domain(base, digits)
    coefficients = tuple(
        base ** (digits - index) - base ** (index - 1)
        for index in range(1, digits // 2 + 1)
    )
    return tuple(
        coefficient
        - (base - 1) * sum(coefficients[index + 1 :])
        for index, coefficient in enumerate(coefficients)
    )


def coefficient_closed_form_slacks(base: int, digits: int) -> tuple[int, ...]:
    """Evaluate the claimed closed form for each dominance slack."""

    _require_domain(base, digits)
    half = digits // 2
    return tuple(
        base ** (digits - half) + base**half - base**index - base ** (index - 1)
        for index in range(1, half + 1)
    )


def _weak_compositions(total: int, parts: int) -> Iterator[tuple[int, ...]]:
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for suffix in _weak_compositions(total - first, parts - 1):
            yield (first,) + suffix


def _multinomial_from_counts(counts: Sequence[int]) -> int:
    """Compute a multinomial as sequential binomial choices, not factorials."""

    remaining = sum(counts)
    ways = 1
    for count in counts:
        ways *= comb(remaining, count)
        remaining -= count
    return ways


def spectrum_weights(base: int, digits: int) -> dict[Spectrum, int]:
    """Independently aggregate every spectrum fiber using digit-count vectors."""

    _require_domain(base, digits)
    result: defaultdict[Spectrum, int] = defaultdict(int)
    for counts in _weak_compositions(digits, base):
        ordered = tuple(_ordered_digits_from_counts(counts, descending=True))
        delta = tuple(
            ordered[index] - ordered[-index - 1]
            for index in range(digits // 2)
        )
        result[delta] += _multinomial_from_counts(counts)
    return dict(result)


def _canonical_cycle(nodes: Sequence[Spectrum]) -> Cycle:
    cycle = tuple(nodes)
    return min(cycle[index:] + cycle[:index] for index in range(len(cycle)))


@dataclass(frozen=True)
class GraphProof:
    successors: Mapping[Spectrum, Spectrum]
    cycles: tuple[Cycle, ...]
    cycle_by_state: Mapping[Spectrum, Cycle]
    depth_by_state: Mapping[Spectrum, int]
    reduced_indegrees: Mapping[Spectrum, int]
    raw_basin_sizes: Mapping[Cycle, int]
    raw_hitting_histogram: Mapping[int, int]


@dataclass(frozen=True)
class DirectGraphProof:
    """Brute-force graph facts obtained only from the direct raw map."""

    cycles: tuple[tuple[int, ...], ...]
    raw_basin_sizes: Mapping[tuple[int, ...], int]
    raw_hitting_histogram: Mapping[int, int]
    raw_indegrees: Mapping[int, int]


def graph_proof(base: int, digits: int, weights: Mapping[Spectrum, int]) -> GraphProof:
    """Classify all orbits independently, restarting from every spectrum."""

    states = spectra(base, digits)
    successors = {
        state: reduced_successor(state, base, digits) for state in states
    }
    cycle_by_state: dict[Spectrum, Cycle] = {}
    depth_by_state: dict[Spectrum, int] = {}
    discovered_cycles: set[Cycle] = set()

    # Deliberately independent of the production graph walk: each state gets a
    # complete local orbit trace, even when a prior trace could be reused.
    for start in states:
        local_position: dict[Spectrum, int] = {}
        orbit: list[Spectrum] = []
        current = start
        while current not in local_position:
            local_position[current] = len(orbit)
            orbit.append(current)
            current = successors[current]
        cycle_start = local_position[current]
        cycle = _canonical_cycle(orbit[cycle_start:])
        discovered_cycles.add(cycle)
        cycle_by_state[start] = cycle
        depth_by_state[start] = cycle_start

    reduced_indegrees = Counter(successors.values())
    basins: Counter[Cycle] = Counter()
    hitting: Counter[int] = Counter()
    for state in states:
        weight = weights[state]
        cycle = cycle_by_state[state]
        depth = depth_by_state[state]
        basins[cycle] += weight
        if depth == 0:
            # Lambda(state) itself is already on the numeric cycle.  All other
            # members of the same spectrum fiber arrive after one raw step.
            hitting[0] += 1
            hitting[1] += weight - 1
        else:
            hitting[depth + 1] += weight

    return GraphProof(
        successors=successors,
        cycles=tuple(sorted(discovered_cycles)),
        cycle_by_state=cycle_by_state,
        depth_by_state=depth_by_state,
        reduced_indegrees=dict(reduced_indegrees),
        raw_basin_sizes=dict(basins),
        raw_hitting_histogram=dict(sorted(hitting.items())),
    )


def _canonical_numeric_cycle(nodes: Sequence[int]) -> tuple[int, ...]:
    cycle = tuple(nodes)
    return min(cycle[index:] + cycle[:index] for index in range(len(cycle)))


def brute_raw_graph(base: int, digits: int) -> DirectGraphProof:
    """Classify every raw orbit directly.

    This intentionally exponential routine is suitable for small cross-checks.
    Unlike :func:`graph_proof`, it knows nothing about spectra, Lambda, reduced
    states, or multinomial weights.
    """

    _require_domain(base, digits)
    basins: Counter[tuple[int, ...]] = Counter()
    hitting: Counter[int] = Counter()
    indegrees: Counter[int] = Counter()
    domain_size = base**digits
    for value in range(domain_size):
        indegrees[direct_kaprekar(value, base, digits)] += 1

        local_position: dict[int, int] = {}
        orbit: list[int] = []
        current = value
        while current not in local_position:
            local_position[current] = len(orbit)
            orbit.append(current)
            current = direct_kaprekar(current, base, digits)
        cycle_start = local_position[current]
        cycle = _canonical_numeric_cycle(orbit[cycle_start:])
        basins[cycle] += 1
        hitting[cycle_start] += 1
    return DirectGraphProof(
        cycles=tuple(sorted(basins)),
        raw_basin_sizes=dict(basins),
        raw_hitting_histogram=dict(sorted(hitting.items())),
        raw_indegrees=dict(indegrees),
    )


def _canonical_json(payload: object) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")


def _record_digest(label: str, records: Iterable[object]) -> str:
    digest = sha256((label + "\n").encode("ascii"))
    for record in records:
        digest.update(_canonical_json(record))
        digest.update(b"\n")
    return digest.hexdigest()


def structural_proof(base: int, digits: int) -> dict[str, object]:
    """Check all finite structural obligations for one arbitrary ``(b, n)``.

    This does not enumerate ``b**n`` raw states.  It proves the reusable
    superincreasing premise, enumerates the complete spectrum state space,
    checks its count, proves a raw representative for every spectrum, and
    verifies conjugacy on every reduced state.
    """

    _require_domain(base, digits)
    states = spectra(base, digits)
    expected_count = comb(base + digits // 2 - 1, base - 1)
    values = tuple(linear_image(state, base, digits) for state in states)
    slacks = coefficient_slacks(base, digits)
    closed_form_slacks = coefficient_closed_form_slacks(base, digits)
    representatives_valid = all(
        spectrum(representative(state, base, digits), base, digits) == state
        for state in states
    )
    conjugacy_valid = all(
        direct_kaprekar(linear_image(state, base, digits), base, digits)
        == linear_image(reduced_successor(state, base, digits), base, digits)
        for state in states
    )
    checks = {
        "spectrum_count_formula": len(states) == expected_count,
        "coefficient_slack_closed_form_identity": slacks == closed_form_slacks,
        "superincreasing_slacks_positive": all(slack > 0 for slack in slacks),
        "lambda_injective": len(set(values)) == len(values),
        "representative_surjectivity": representatives_valid,
        "post_first_step_conjugacy": conjugacy_valid,
    }
    if not all(checks.values()):
        raise AssertionError(f"structural proof failed for base={base}, digits={digits}")
    return {
        "base": base,
        "digits": digits,
        "spectrum_states": len(states),
        "expected_spectrum_states": expected_count,
        "minimum_superincreasing_slack": min(slacks) if slacks else None,
        "checks": checks,
        "lambda_image_sha256": _record_digest(
            "kaprekar-independent-lambda-v1",
            (([*state], value) for state, value in zip(states, values)),
        ),
    }


def exhaustive_case_proof(base: int, digits: int) -> dict[str, object]:
    """Prove one finite system by exhaustive raw and reduced enumeration."""

    structural = structural_proof(base, digits)
    states = spectra(base, digits)
    image_values = {linear_image(state, base, digits) for state in states}
    direct_image: set[int] = set()
    direct_fibers: Counter[Spectrum] = Counter()
    raw_transition_digest = sha256(
        b"kaprekar-independent-raw-v1\n"
    )
    factorization_valid = True
    for value in range(base**digits):
        delta = spectrum(value, base, digits)
        direct = direct_kaprekar(value, base, digits)
        factored = linear_image(delta, base, digits)
        factorization_valid = factorization_valid and direct == factored
        direct_image.add(direct)
        direct_fibers[delta] += 1
        raw_transition_digest.update(
            _canonical_json((value, direct, list(delta)))
        )
        raw_transition_digest.update(b"\n")

    weights = spectrum_weights(base, digits)
    graph = graph_proof(base, digits, weights)
    attached_leaf_counts = {
        state: weights[state] - graph.reduced_indegrees.get(state, 0)
        for state in states
    }
    graph_checks = {
        "multiset_weights_match_raw_fibers": weights == dict(direct_fibers),
        "weights_cover_raw_domain": sum(weights.values()) == base**digits,
        "all_spectra_have_positive_weight": set(weights) == set(states)
        and all(weight > 0 for weight in weights.values()),
        "reduced_indegrees_sum_to_state_count": (
            sum(graph.reduced_indegrees.values()) == len(states)
        ),
        "full_indegrees_sum_to_raw_count": sum(weights.values()) == base**digits,
        "attached_leaves_nonnegative": all(
            count >= 0 for count in attached_leaf_counts.values()
        ),
        "attached_leaves_sum_identity": (
            sum(attached_leaf_counts.values()) == base**digits - len(states)
        ),
        "raw_basins_partition_domain": (
            sum(graph.raw_basin_sizes.values()) == base**digits
        ),
        "raw_hitting_histogram_partitions_domain": (
            sum(graph.raw_hitting_histogram.values()) == base**digits
        ),
    }
    checks = {
        **structural["checks"],
        "raw_factorization_exhaustive": factorization_valid,
        "raw_image_equals_lambda_image": direct_image == image_values,
        "raw_image_cardinality": len(direct_image) == len(states),
        **graph_checks,
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise AssertionError(
            f"exhaustive proof failed for base={base}, digits={digits}: {failed}"
        )

    cycles = []
    for cycle in graph.cycles:
        cycles.append(
            {
                "spectrum_cycle": [list(state) for state in cycle],
                "numeric_cycle": [linear_image(state, base, digits) for state in cycle],
                "raw_basin_size": graph.raw_basin_sizes[cycle],
                "maximum_reduced_depth": max(
                    graph.depth_by_state[state]
                    for state in states
                    if graph.cycle_by_state[state] == cycle
                ),
            }
        )

    return {
        "base": base,
        "digits": digits,
        "proof_mode": "exhaustive_raw_and_reduced_integer_arithmetic",
        "raw_states_checked": base**digits,
        "spectrum_states_checked": len(states),
        "minimum_superincreasing_slack": structural[
            "minimum_superincreasing_slack"
        ],
        "checks": checks,
        "cycles": cycles,
        "raw_hitting_histogram": {
            str(step): count for step, count in graph.raw_hitting_histogram.items()
        },
        "commitments": {
            "raw_transition_sha256": raw_transition_digest.hexdigest(),
            "reduced_graph_sha256": _record_digest(
                "kaprekar-independent-reduced-v1",
                (
                    (
                        [*state],
                        [*graph.successors[state]],
                        weights[state],
                        graph.reduced_indegrees.get(state, 0),
                        attached_leaf_counts[state],
                    )
                    for state in states
                )
            ),
            "raw_weights_sha256": _record_digest(
                "kaprekar-independent-weights-v1",
                (([*state], weights[state]) for state in states),
            ),
        },
    }


def build_certificate(
    *,
    base_min: int = 2,
    base_max: int = 8,
    digits_min: int = 1,
    digits_max: int = 7,
) -> dict[str, object]:
    """Build a deterministic exhaustive proof certificate for a finite grid."""

    if base_min > base_max or digits_min > digits_max:
        raise ValueError("certificate bounds must define nonempty ranges")
    cases = [
        exhaustive_case_proof(base, digits)
        for base in range(base_min, base_max + 1)
        for digits in range(digits_min, digits_max + 1)
    ]
    body: dict[str, object] = {
        "schema": CERTIFICATE_SCHEMA,
        "epistemic_status": {
            "universal_claim": (
                "The algebraic proof in paper/theory_addendum.md is universal; "
                "this artifact is a finite exhaustive proof over its declared grid."
            ),
            "independence": (
                "Generated by proofs/independent_oracle.py without importing "
                "the production kaprekar package."
            ),
        },
        "scope": {
            "base_min": base_min,
            "base_max": base_max,
            "digits_min": digits_min,
            "digits_max": digits_max,
            "case_count": len(cases),
            "raw_states_checked": sum(case["raw_states_checked"] for case in cases),
            "spectrum_states_checked": sum(
                case["spectrum_states_checked"] for case in cases
            ),
        },
        "cases": cases,
    }
    body["certificate_sha256"] = sha256(_canonical_json(body)).hexdigest()
    return body


def verify_certificate_envelope(payload: Mapping[str, object]) -> None:
    """Verify schema, top-level digest, scope totals, and every asserted check."""

    if payload.get("schema") != CERTIFICATE_SCHEMA:
        raise ValueError("unrecognized certificate schema")
    expected_digest = payload.get("certificate_sha256")
    if not isinstance(expected_digest, str) or len(expected_digest) != 64:
        raise ValueError("certificate has no valid SHA-256 field")
    body = dict(payload)
    del body["certificate_sha256"]
    actual_digest = sha256(_canonical_json(body)).hexdigest()
    if actual_digest != expected_digest:
        raise ValueError("certificate SHA-256 mismatch")

    cases = payload.get("cases")
    scope = payload.get("scope")
    if not isinstance(cases, list) or not isinstance(scope, dict):
        raise ValueError("certificate cases or scope are malformed")
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("checks"), dict):
            raise ValueError("certificate case is malformed")
        if not all(value is True for value in case["checks"].values()):
            raise ValueError("certificate contains a failed proof obligation")
    if scope.get("case_count") != len(cases):
        raise ValueError("certificate case count is inconsistent")
    if scope.get("raw_states_checked") != sum(
        case["raw_states_checked"] for case in cases
    ):
        raise ValueError("certificate raw-state total is inconsistent")
    if scope.get("spectrum_states_checked") != sum(
        case["spectrum_states_checked"] for case in cases
    ):
        raise ValueError("certificate spectrum-state total is inconsistent")


def recompute_and_verify_certificate(payload: Mapping[str, object]) -> None:
    """Recompute the entire declared grid and require byte-level equality."""

    verify_certificate_envelope(payload)
    scope = payload["scope"]
    assert isinstance(scope, dict)
    recomputed = build_certificate(
        base_min=int(scope["base_min"]),
        base_max=int(scope["base_max"]),
        digits_min=int(scope["digits_min"]),
        digits_max=int(scope["digits_max"]),
    )
    if recomputed != payload:
        raise ValueError("recomputed certificate differs from the supplied artifact")


__all__ = [
    "CERTIFICATE_SCHEMA",
    "DirectGraphProof",
    "GraphProof",
    "build_certificate",
    "brute_raw_graph",
    "coefficient_closed_form_slacks",
    "coefficient_slacks",
    "direct_kaprekar",
    "exhaustive_case_proof",
    "graph_proof",
    "linear_image",
    "radix_vector",
    "recompute_and_verify_certificate",
    "reduced_successor",
    "representative",
    "spectra",
    "spectrum",
    "spectrum_weights",
    "structural_proof",
    "verify_certificate_envelope",
]
