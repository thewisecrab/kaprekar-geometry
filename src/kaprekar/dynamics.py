"""Exact reduced-state dynamics and raw-state aggregation."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations_with_replacement, groupby
from math import factorial, log2
from typing import Sequence

from .core import (
    ComputationLimitError,
    Spectrum,
    digit_multiset_count,
    enumerate_spectra,
    kaprekar_map,
    lambda_bn,
    require_bool,
    require_int,
    spectrum_count,
    spectrum_of_number,
    validate_base_and_digits,
    validate_spectrum,
)


DEFAULT_SPECTRUM_LIMIT = 1_000_000
DEFAULT_MULTISET_LIMIT = 2_000_000
DEFAULT_DYNAMICS_WORK_UNIT_LIMIT = 50_000_000
DEFAULT_DYNAMICS_DIGIT_LIMIT = 4_096


def _enforce_limit(
    label: str,
    requested: int,
    limit: int,
    force: bool,
) -> None:
    require_int(label, requested, minimum=0)
    maximum = require_int("limit", limit, minimum=1)
    bypass = require_bool("force", force)
    if requested > maximum and not bypass:
        raise ComputationLimitError(
            f"{label} requires {requested:,} states, above the {maximum:,} limit; "
            "raise the limit or pass force=True explicitly"
        )


def _enforce_digit_limit(digits: int, limit: int, force: bool) -> None:
    maximum = require_int("max_digits", limit, minimum=1)
    bypass = require_bool("force", force)
    if digits > maximum and not bypass:
        raise ComputationLimitError(
            f"digit count {digits:,} exceeds the {maximum:,} digit limit; "
            "raise the limit or pass force=True explicitly"
        )


def reduced_map(delta: Sequence[int], b: int, n: int) -> Spectrum:
    """Apply R_(b,n) = Sigma o Lambda to one valid spectrum."""

    spectrum = validate_spectrum(delta, b, n)
    return spectrum_of_number(lambda_bn(spectrum, b, n), b, n)


def fixed_spectra(
    b: int,
    n: int,
    *,
    include_zero: bool = False,
    max_spectra: int = DEFAULT_SPECTRUM_LIMIT,
    max_work_units: int = DEFAULT_DYNAMICS_WORK_UNIT_LIMIT,
    max_digits: int = DEFAULT_DYNAMICS_DIGIT_LIMIT,
    force: bool = False,
) -> list[tuple[Spectrum, int]]:
    """Return all fixed spectra and their corresponding Kaprekar fixed points."""

    base, digit_count = validate_base_and_digits(b, n)
    include_zero = require_bool("include_zero", include_zero)
    force = require_bool("force", force)
    _enforce_digit_limit(digit_count, max_digits, force)
    count = spectrum_count(base, digit_count)
    _enforce_limit("fixed-spectrum search", count, max_spectra, force)
    _enforce_limit(
        "fixed-spectrum digit-state work",
        count * digit_count,
        max_work_units,
        force,
    )
    fixed: list[tuple[Spectrum, int]] = []
    for spectrum in enumerate_spectra(base, digit_count):
        value = lambda_bn(spectrum, base, digit_count)
        if (include_zero or value != 0) and spectrum_of_number(
            value, base, digit_count
        ) == spectrum:
            fixed.append((spectrum, value))
    return fixed


def decimal_fixed_spectra(n: int) -> list[tuple[Spectrum, int]]:
    """Backward-compatible decimal specialization of :func:`fixed_spectra`."""

    return fixed_spectra(10, n)


def _multinomial_weight(
    sorted_digits: tuple[int, ...],
    numerator: int,
) -> int:
    weight = numerator
    for _, group in groupby(sorted_digits):
        weight //= factorial(sum(1 for _ in group))
    return weight


def raw_spectrum_weights(
    b: int,
    n: int,
    *,
    max_multisets: int = DEFAULT_MULTISET_LIMIT,
    max_work_units: int = DEFAULT_DYNAMICS_WORK_UNIT_LIMIT,
    max_digits: int = DEFAULT_DYNAMICS_DIGIT_LIMIT,
    force: bool = False,
) -> dict[Spectrum, int]:
    """Count raw digit strings in every spectrum class exactly.

    The algorithm enumerates sorted digit multisets rather than all ``b**n`` raw
    strings. Each multiset contributes its multinomial number of permutations to
    the corresponding spectrum, preserving leading-zero states exactly.
    """

    base, digit_count = validate_base_and_digits(b, n)
    force = require_bool("force", force)
    _enforce_digit_limit(digit_count, max_digits, force)
    multiset_count = digit_multiset_count(base, digit_count)
    _enforce_limit("raw spectrum weighting", multiset_count, max_multisets, force)
    _enforce_limit(
        "raw-weight digit-state work",
        multiset_count * digit_count,
        max_work_units,
        force,
    )

    weights: defaultdict[Spectrum, int] = defaultdict(int)
    digit_alphabet = range(base - 1, -1, -1)
    permutation_numerator = factorial(digit_count)
    for sorted_digits in combinations_with_replacement(digit_alphabet, digit_count):
        spectrum = tuple(
            sorted_digits[index] - sorted_digits[-1 - index]
            for index in range(digit_count // 2)
        )
        weights[spectrum] += _multinomial_weight(
            sorted_digits,
            permutation_numerator,
        )

    result = dict(weights)
    if len(result) != spectrum_count(base, digit_count):
        raise AssertionError(
            "raw multiset aggregation did not reach every valid spectrum"
        )
    if sum(result.values()) != base**digit_count:
        raise AssertionError("raw spectrum weights do not sum to b**n")
    return result


def _canonical_cycle(cycle: Sequence[Spectrum]) -> tuple[Spectrum, ...]:
    nodes = tuple(cycle)
    if not nodes:
        raise AssertionError("functional graph cycle cannot be empty")
    rotations = (nodes[index:] + nodes[:index] for index in range(len(nodes)))
    return min(rotations)


@dataclass(frozen=True, slots=True)
class StateAnalysis:
    """Exact metadata for one reduced spectrum state."""

    spectrum: Spectrum
    successor: Spectrum
    attractor_id: int
    reduced_depth: int
    raw_weight: int | None
    reduced_indegree: int
    raw_indegree: int | None
    attached_leaf_count: int | None

    def to_dict(self) -> dict[str, object]:
        return {
            "spectrum": list(self.spectrum),
            "successor": list(self.successor),
            "attractor_id": self.attractor_id,
            "reduced_depth": self.reduced_depth,
            "raw_weight": self.raw_weight,
            "reduced_indegree": self.reduced_indegree,
            "raw_indegree": self.raw_indegree,
            "attached_leaf_count": self.attached_leaf_count,
        }


@dataclass(frozen=True, slots=True)
class AttractorAnalysis:
    """A cycle and the exact reduced/raw basin feeding it."""

    attractor_id: int
    cycle_spectra: tuple[Spectrum, ...]
    cycle_values: tuple[int, ...]
    reduced_basin_size: int
    raw_basin_size: int | None
    maximum_reduced_depth: int
    spectrum_convergence_histogram: tuple[tuple[int, int], ...]
    raw_convergence_histogram: tuple[tuple[int, int], ...] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "attractor_id": self.attractor_id,
            "cycle_length": len(self.cycle_spectra),
            "cycle_spectra": [list(spectrum) for spectrum in self.cycle_spectra],
            "cycle_values": list(self.cycle_values),
            "reduced_basin_size": self.reduced_basin_size,
            "raw_basin_size": self.raw_basin_size,
            "maximum_reduced_depth": self.maximum_reduced_depth,
            "spectrum_convergence_histogram": {
                str(depth): count
                for depth, count in self.spectrum_convergence_histogram
            },
            "raw_convergence_histogram": (
                None
                if self.raw_convergence_histogram is None
                else {
                    str(steps): count
                    for steps, count in self.raw_convergence_histogram
                }
            ),
        }


@dataclass(frozen=True, slots=True)
class FunctionalGraphAnalysis:
    """Complete functional graph over S_(b,n), optionally weighted by raw states."""

    base: int
    digits: int
    spectrum_state_count: int
    raw_state_count: int
    raw_weights_included: bool
    states: tuple[StateAnalysis, ...]
    attractors: tuple[AttractorAnalysis, ...]
    spectrum_convergence_histogram: tuple[tuple[int, int], ...]
    raw_convergence_histogram: tuple[tuple[int, int], ...] | None
    graph_sha256: str

    def to_dict(self, *, include_states: bool = True) -> dict[str, object]:
        result: dict[str, object] = {
            "base": self.base,
            "digits": self.digits,
            "spectrum_state_count": self.spectrum_state_count,
            "raw_state_count": self.raw_state_count,
            "raw_weights_included": self.raw_weights_included,
            "graph_sha256": self.graph_sha256,
            "attractor_count": len(self.attractors),
            "attractors": [attractor.to_dict() for attractor in self.attractors],
            "spectrum_convergence_histogram": {
                str(depth): count
                for depth, count in self.spectrum_convergence_histogram
            },
            "raw_convergence_histogram": (
                None
                if self.raw_convergence_histogram is None
                else {
                    str(steps): count
                    for steps, count in self.raw_convergence_histogram
                }
            ),
        }
        if include_states:
            result["states"] = [state.to_dict() for state in self.states]
        return result


def analyze_functional_graph(
    b: int,
    n: int,
    *,
    include_raw_weights: bool = True,
    max_spectra: int = DEFAULT_SPECTRUM_LIMIT,
    max_multisets: int = DEFAULT_MULTISET_LIMIT,
    max_work_units: int = DEFAULT_DYNAMICS_WORK_UNIT_LIMIT,
    max_digits: int = DEFAULT_DYNAMICS_DIGIT_LIMIT,
    force: bool = False,
) -> FunctionalGraphAnalysis:
    """Analyze every reduced transition, cycle, basin, and convergence depth exactly.

    When raw weights are requested, ``raw_convergence_histogram`` counts actual
    Kaprekar iterations needed by each of the ``b**n`` raw numbers to enter a
    numeric attractor. Reduced cycle states contribute one already-cyclic raw
    number at step zero; other raw numbers in those spectrum classes enter in one
    step. A noncycle spectrum at reduced depth d enters after d+1 raw steps.
    """

    base, digit_count = validate_base_and_digits(b, n)
    include_raw_weights = require_bool("include_raw_weights", include_raw_weights)
    force = require_bool("force", force)
    _enforce_digit_limit(digit_count, max_digits, force)
    state_count = spectrum_count(base, digit_count)
    _enforce_limit("functional graph analysis", state_count, max_spectra, force)
    multiset_count = 0
    if include_raw_weights:
        multiset_count = digit_multiset_count(base, digit_count)
        _enforce_limit(
            "raw spectrum weighting",
            multiset_count,
            max_multisets,
            force,
        )
    _enforce_limit(
        "functional-graph digit-state work",
        (state_count + multiset_count) * digit_count,
        max_work_units,
        force,
    )

    spectra = tuple(enumerate_spectra(base, digit_count))
    successors = {
        spectrum: reduced_map(spectrum, base, digit_count) for spectrum in spectra
    }
    if any(successor not in successors for successor in successors.values()):
        raise AssertionError("reduced map left the declared spectrum state space")

    depth_by_state: dict[Spectrum, int] = {}
    cycle_key_by_state: dict[Spectrum, tuple[Spectrum, ...]] = {}
    cycles: dict[tuple[Spectrum, ...], tuple[Spectrum, ...]] = {}

    for start in spectra:
        if start in depth_by_state:
            continue
        path: list[Spectrum] = []
        local_index: dict[Spectrum, int] = {}
        current = start
        while current not in depth_by_state and current not in local_index:
            local_index[current] = len(path)
            path.append(current)
            current = successors[current]

        if current in local_index:
            cycle_start = local_index[current]
            cycle_key = _canonical_cycle(path[cycle_start:])
            cycles[cycle_key] = cycle_key
            for state in path[cycle_start:]:
                depth_by_state[state] = 0
                cycle_key_by_state[state] = cycle_key
            prefix = path[:cycle_start]
        else:
            prefix = path

        for state in reversed(prefix):
            successor = successors[state]
            depth_by_state[state] = depth_by_state[successor] + 1
            cycle_key_by_state[state] = cycle_key_by_state[successor]

    ordered_cycles = tuple(sorted(cycles))
    attractor_id_by_key = {
        cycle_key: index for index, cycle_key in enumerate(ordered_cycles)
    }

    weights: dict[Spectrum, int] | None
    if include_raw_weights:
        weights = raw_spectrum_weights(
            base,
            digit_count,
            max_multisets=max_multisets,
            max_work_units=max_work_units,
            max_digits=max_digits,
            force=force,
        )
    else:
        weights = None

    reduced_indegrees = Counter(successors.values())
    certificate = sha256()
    certificate.update(f"kaprekar-graph-v1\nb={base}\nn={digit_count}\n".encode("ascii"))
    for spectrum in spectra:
        certificate.update(
            repr((spectrum, successors[spectrum], None if weights is None else weights[spectrum])).encode(
                "ascii"
            )
        )
        certificate.update(b"\n")

    reduced_basin_sizes: Counter[int] = Counter()
    raw_basin_sizes: Counter[int] = Counter()
    spectrum_histograms: dict[int, Counter[int]] = defaultdict(Counter)
    raw_histograms: dict[int, Counter[int]] = defaultdict(Counter)
    global_spectrum_histogram: Counter[int] = Counter()
    global_raw_histogram: Counter[int] = Counter()
    maximum_depths: Counter[int] = Counter()

    state_analyses: list[StateAnalysis] = []
    for spectrum in spectra:
        attractor_id = attractor_id_by_key[cycle_key_by_state[spectrum]]
        depth = depth_by_state[spectrum]
        weight = None if weights is None else weights[spectrum]
        reduced_indegree = reduced_indegrees[spectrum]
        reduced_basin_sizes[attractor_id] += 1
        spectrum_histograms[attractor_id][depth] += 1
        global_spectrum_histogram[depth] += 1
        maximum_depths[attractor_id] = max(maximum_depths[attractor_id], depth)

        if weight is not None:
            raw_basin_sizes[attractor_id] += weight
            if depth == 0:
                raw_histograms[attractor_id][0] += 1
                global_raw_histogram[0] += 1
                if weight > 1:
                    raw_histograms[attractor_id][1] += weight - 1
                    global_raw_histogram[1] += weight - 1
            else:
                raw_histograms[attractor_id][depth + 1] += weight
                global_raw_histogram[depth + 1] += weight

        state_analyses.append(
            StateAnalysis(
                spectrum=spectrum,
                successor=successors[spectrum],
                attractor_id=attractor_id,
                reduced_depth=depth,
                raw_weight=weight,
                reduced_indegree=reduced_indegree,
                raw_indegree=weight,
                attached_leaf_count=(
                    None if weight is None else weight - reduced_indegree
                ),
            )
        )

    attractors: list[AttractorAnalysis] = []
    for attractor_id, cycle in enumerate(ordered_cycles):
        cycle_values = tuple(
            lambda_bn(spectrum, base, digit_count) for spectrum in cycle
        )
        for index, value in enumerate(cycle_values):
            if kaprekar_map(value, base, digit_count) != cycle_values[
                (index + 1) % len(cycle_values)
            ]:
                raise AssertionError("reported numeric attractor is not a cycle")
        attractors.append(
            AttractorAnalysis(
                attractor_id=attractor_id,
                cycle_spectra=cycle,
                cycle_values=cycle_values,
                reduced_basin_size=reduced_basin_sizes[attractor_id],
                raw_basin_size=(
                    None
                    if weights is None
                    else raw_basin_sizes[attractor_id]
                ),
                maximum_reduced_depth=maximum_depths[attractor_id],
                spectrum_convergence_histogram=tuple(
                    sorted(spectrum_histograms[attractor_id].items())
                ),
                raw_convergence_histogram=(
                    None
                    if weights is None
                    else tuple(sorted(raw_histograms[attractor_id].items()))
                ),
            )
        )

    if sum(reduced_basin_sizes.values()) != state_count:
        raise AssertionError("reduced basin sizes do not cover the state space")
    if weights is not None:
        if sum(raw_basin_sizes.values()) != base**digit_count:
            raise AssertionError("raw basin sizes do not cover the raw state space")
        if sum(global_raw_histogram.values()) != base**digit_count:
            raise AssertionError("raw convergence histogram lost raw states")

    return FunctionalGraphAnalysis(
        base=base,
        digits=digit_count,
        spectrum_state_count=state_count,
        raw_state_count=base**digit_count,
        raw_weights_included=weights is not None,
        states=tuple(state_analyses),
        attractors=tuple(attractors),
        spectrum_convergence_histogram=tuple(
            sorted(global_spectrum_histogram.items())
        ),
        raw_convergence_histogram=(
            None
            if weights is None
            else tuple(sorted(global_raw_histogram.items()))
        ),
        graph_sha256=certificate.hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class EntropyPoint:
    """Exact support and Shannon entropy after a number of raw Kaprekar steps."""

    iteration: int
    entropy_bits: float
    support_size: int

    def to_dict(self) -> dict[str, int | float]:
        return {
            "iteration": self.iteration,
            "entropy_bits": self.entropy_bits,
            "support_size": self.support_size,
        }


def _entropy_bits(masses: Sequence[int], total: int) -> float:
    log_total = log2(total)
    entropy = 0.0
    for mass in masses:
        if mass <= 0:
            continue
        probability = mass / total
        if probability > 0.0:
            entropy -= probability * (log2(mass) - log_total)
    return entropy


def uniform_entropy_trajectory(
    analysis: FunctionalGraphAnalysis,
    *,
    through_iteration: int | None = None,
) -> tuple[EntropyPoint, ...]:
    """Return the exact entropy funnel for a uniform raw-state input law.

    Iteration zero is uniform on all ``b**n`` raw states. Iteration one is the
    spectrum-fiber distribution relabeled through Lambda; later iterations
    propagate that law through the exact reduced map.
    """

    if not isinstance(analysis, FunctionalGraphAnalysis):
        raise TypeError("analysis must be a FunctionalGraphAnalysis")
    if not analysis.raw_weights_included:
        raise ValueError("raw weights are required for the uniform entropy trajectory")
    if through_iteration is not None:
        through_iteration = require_int(
            "through_iteration", through_iteration, minimum=0
        )
    else:
        maximum_depth = max(state.reduced_depth for state in analysis.states)
        through_iteration = maximum_depth + 1

    total = analysis.raw_state_count
    points = [
        EntropyPoint(
            iteration=0,
            entropy_bits=log2(total),
            support_size=total,
        )
    ]
    if through_iteration == 0:
        return tuple(points)

    distribution = {
        state.spectrum: state.raw_weight
        for state in analysis.states
        if state.raw_weight is not None and state.raw_weight > 0
    }
    successors = {state.spectrum: state.successor for state in analysis.states}
    points.append(
        EntropyPoint(
            iteration=1,
            entropy_bits=_entropy_bits(tuple(distribution.values()), total),
            support_size=len(distribution),
        )
    )
    for iteration in range(2, through_iteration + 1):
        next_distribution: Counter[Spectrum] = Counter()
        for spectrum, mass in distribution.items():
            next_distribution[successors[spectrum]] += mass
        distribution = dict(next_distribution)
        points.append(
            EntropyPoint(
                iteration=iteration,
                entropy_bits=_entropy_bits(tuple(distribution.values()), total),
                support_size=len(distribution),
            )
        )
    return tuple(points)


__all__ = [
    "AttractorAnalysis",
    "DEFAULT_MULTISET_LIMIT",
    "DEFAULT_SPECTRUM_LIMIT",
    "DEFAULT_DYNAMICS_DIGIT_LIMIT",
    "DEFAULT_DYNAMICS_WORK_UNIT_LIMIT",
    "EntropyPoint",
    "FunctionalGraphAnalysis",
    "StateAnalysis",
    "analyze_functional_graph",
    "decimal_fixed_spectra",
    "fixed_spectra",
    "raw_spectrum_weights",
    "reduced_map",
    "uniform_entropy_trajectory",
]
