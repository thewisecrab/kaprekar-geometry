"""Numerically safe normalized-gap diagnostics for ordered logit spectra.

The functions in this module deliberately separate mathematical identities from
deployment claims.  In particular, :func:`relaxed_margin_diagnostic` is an
audit signal; using it as an acceptance rule does *not* preserve a target
model's sampling distribution.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isclose, isfinite, log
from numbers import Real
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class GapSimplex:
    """Normalized adjacent gaps for the sorted top-k logits.

    ``coordinates`` is ``None`` when the top-k spread is at or below the
    requested tolerance.  That case is mathematically undefined rather than a
    vector of zeros; callers must retain the ``degenerate`` flag. ``entropy``
    is the full-distribution Shannon entropy in nats.
    """

    sorted_logits: tuple[float, ...]
    top_indices: tuple[int, ...]
    spread: float
    coordinates: tuple[float, ...] | None
    degenerate: bool
    top_k_probability_mass: float
    max_probability: float
    entropy: float

    @property
    def k(self) -> int:
        return len(self.sorted_logits)

    @property
    def shape_degrees_of_freedom(self) -> int:
        """Dimension of the affine quotient represented by the coordinates."""

        return max(self.k - 2, 0)

    def normalized_loss(self, rank: int) -> float:
        """Return ``(s_1 - s_rank) / (s_1 - s_k)`` for a one-based rank."""

        if not isinstance(rank, int) or isinstance(rank, bool):
            raise TypeError("rank must be an integer")
        if not 1 <= rank <= self.k:
            raise ValueError(f"rank must be in [1, {self.k}]")
        if self.coordinates is None:
            raise ValueError("normalized loss is undefined for a flat top-k spectrum")
        return sum(self.coordinates[: rank - 1])

    def probability_ratio(self, rank: int) -> float:
        """Return the exact softmax ratio ``p_rank / p_1``."""

        if not isinstance(rank, int) or isinstance(rank, bool):
            raise TypeError("rank must be an integer")
        if not 1 <= rank <= self.k:
            raise ValueError(f"rank must be in [1, {self.k}]")
        return exp(self.sorted_logits[rank - 1] - self.sorted_logits[0])


@dataclass(frozen=True, slots=True)
class TailMassBounds:
    """Sharp bounds implied by top-k values when all tail logits are unknown."""

    top_k_mass_lower: float
    top_k_mass_upper: float
    top1_probability_lower: float
    top1_probability_upper: float


@dataclass(frozen=True, slots=True)
class MarginDiagnostic:
    """Transparent diagnostics for a normalized target-logit margin rule."""

    accepted: bool
    candidate_index: int
    rank: int
    normalized_loss: float | None
    exact_probability_ratio: float
    certified_ratio_lower_bound: float | None
    reason: str


def _as_finite_logits(logits: Iterable[Real]) -> tuple[float, ...]:
    if isinstance(logits, (str, bytes)):
        raise TypeError("logits must be a finite sequence of real numbers")
    try:
        raw_values = tuple(logits)
    except TypeError as error:
        raise TypeError("logits must be a finite iterable of real numbers") from error
    if len(raw_values) < 2:
        raise ValueError("at least two logits are required")

    values: list[float] = []
    for position, value in enumerate(raw_values):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"logit at position {position} is not a real number")
        converted = float(value)
        if not isfinite(converted):
            raise ValueError(f"logit at position {position} is not finite")
        values.append(converted)
    return tuple(values)


def _validate_k(k: int | None, vocabulary_size: int) -> int:
    if k is None:
        return vocabulary_size
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")
    if not 2 <= k <= vocabulary_size:
        raise ValueError(f"k must be in [2, {vocabulary_size}]")
    return k


def _softmax_statistics(values: tuple[float, ...], top_indices: tuple[int, ...]) -> tuple[float, float, float]:
    maximum = max(values)
    weights = [exp(value - maximum) for value in values]
    normalizer = sum(weights)
    probabilities = [weight / normalizer for weight in weights]
    max_probability = max(probabilities)
    entropy = -sum(probability * log(probability) for probability in probabilities if probability > 0.0)
    top_k_mass = sum(probabilities[index] for index in top_indices)
    return top_k_mass, max_probability, entropy


def gap_simplex(
    logits: Iterable[Real],
    *,
    k: int | None = None,
    flat_tolerance: float = 0.0,
) -> GapSimplex:
    """Compute normalized adjacent gaps and full-distribution diagnostics.

    Sorting is deterministic under ties: lower original token indices come
    first.  Temperature scaling changes ``spread`` but not nondegenerate gap
    coordinates; additive shifts change neither.
    """

    values = _as_finite_logits(logits)
    selected_k = _validate_k(k, len(values))
    if isinstance(flat_tolerance, bool) or not isinstance(flat_tolerance, Real):
        raise TypeError("flat_tolerance must be a real number")
    tolerance = float(flat_tolerance)
    if not isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("flat_tolerance must be finite and non-negative")

    ranked = sorted(range(len(values)), key=lambda index: (-values[index], index))[:selected_k]
    top_indices = tuple(ranked)
    sorted_logits = tuple(values[index] for index in top_indices)
    spread = sorted_logits[0] - sorted_logits[-1]
    if not isfinite(spread):
        raise ValueError("top-k spread overflowed; rescale the logits before analysis")

    if spread <= tolerance:
        coordinates: tuple[float, ...] | None = None
        degenerate = True
    else:
        gaps = tuple(
            (sorted_logits[index] - sorted_logits[index + 1]) / spread
            for index in range(selected_k - 1)
        )
        # Floating-point subtraction can leave the sum a few ulps from one.
        if not isclose(sum(gaps), 1.0, rel_tol=1e-12, abs_tol=1e-12):
            raise ArithmeticError("normalized adjacent gaps failed to sum to one")
        coordinates = gaps
        degenerate = False

    top_k_mass, max_probability, entropy = _softmax_statistics(values, top_indices)
    return GapSimplex(
        sorted_logits=sorted_logits,
        top_indices=top_indices,
        spread=spread,
        coordinates=coordinates,
        degenerate=degenerate,
        top_k_probability_mass=top_k_mass,
        max_probability=max_probability,
        entropy=entropy,
    )


def reconstruct_sorted_logits(
    spread: Real,
    coordinates: Sequence[Real],
    *,
    anchor: Real = 0.0,
) -> tuple[float, ...]:
    """Reconstruct sorted logits from spread and simplex coordinates."""

    if isinstance(spread, bool) or not isinstance(spread, Real):
        raise TypeError("spread must be a real number")
    distance = float(spread)
    if not isfinite(distance) or distance <= 0.0:
        raise ValueError("spread must be finite and strictly positive")
    if isinstance(anchor, bool) or not isinstance(anchor, Real):
        raise TypeError("anchor must be a real number")
    base = float(anchor)
    if not isfinite(base):
        raise ValueError("anchor must be finite")

    if isinstance(coordinates, (str, bytes)) or not isinstance(coordinates, Sequence):
        raise TypeError("coordinates must be a sequence")
    if not coordinates:
        raise ValueError("at least one coordinate is required")
    normalized: list[float] = []
    for position, value in enumerate(coordinates):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"coordinate at position {position} is not real")
        converted = float(value)
        if not isfinite(converted) or converted < 0.0:
            raise ValueError("coordinates must be finite and non-negative")
        normalized.append(converted)
    if not isclose(sum(normalized), 1.0, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("coordinates must sum to one")

    suffix = 0.0
    reversed_values = [base]
    for gap in reversed(normalized):
        suffix += gap
        reversed_values.append(base + distance * suffix)
    return tuple(reversed(reversed_values))


def tail_mass_bounds(summary: GapSimplex, vocabulary_size: int) -> TailMassBounds:
    """Bound omitted tail mass using only top-k values and vocabulary size.

    The lower bounds are attained when every omitted logit ties ``s_k``.  For
    a nonempty finite tail, the upper bounds are strict suprema approached as
    all omitted logits tend to negative infinity.  When
    ``k == vocabulary_size`` there is no tail and both bounds collapse to the
    exact values.
    """

    if not isinstance(vocabulary_size, int) or isinstance(vocabulary_size, bool):
        raise TypeError("vocabulary_size must be an integer")
    if vocabulary_size < summary.k:
        raise ValueError("vocabulary_size cannot be smaller than k")

    relative = tuple(value - summary.sorted_logits[-1] for value in summary.sorted_logits)
    maximum = max(relative)
    log_top_partition = maximum + log(sum(exp(value - maximum) for value in relative))
    omitted = vocabulary_size - summary.k
    if omitted == 0:
        top_k_lower = top_k_upper = 1.0
        top1 = exp(relative[0] - log_top_partition)
        top1_lower = top1_upper = top1
    else:
        tail_to_top = omitted * exp(-log_top_partition)
        top_k_lower = 1.0 / (1.0 + tail_to_top)
        top_k_upper = 1.0
        conditional_top1 = exp(relative[0] - log_top_partition)
        top1_lower = conditional_top1 * top_k_lower
        top1_upper = conditional_top1
    return TailMassBounds(
        top_k_mass_lower=top_k_lower,
        top_k_mass_upper=top_k_upper,
        top1_probability_lower=top1_lower,
        top1_probability_upper=top1_upper,
    )


def relaxed_margin_diagnostic(
    logits: Iterable[Real],
    candidate_index: int,
    *,
    k: int,
    rho: Real,
    absolute_margin_cap: Real | None = None,
    flat_tolerance: float = 0.0,
) -> MarginDiagnostic:
    """Evaluate the manuscript's normalized-margin condition safely.

    This function does not perform speculative decoding and does not preserve a
    target distribution.  It reports only the exact target probability ratio
    and the lower bound implied by the proposed condition. Supplying an
    absolute margin cap applies the addendum's dual normalized/absolute gate;
    it still does not make the rule distribution-preserving.
    """

    values = _as_finite_logits(logits)
    if not isinstance(candidate_index, int) or isinstance(candidate_index, bool):
        raise TypeError("candidate_index must be an integer")
    if not 0 <= candidate_index < len(values):
        raise ValueError(f"candidate_index must be in [0, {len(values) - 1}]")
    if isinstance(rho, bool) or not isinstance(rho, Real):
        raise TypeError("rho must be a real number")
    threshold = float(rho)
    if not isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("rho must be finite and in [0, 1]")
    if absolute_margin_cap is None:
        absolute_cap = None
    else:
        if isinstance(absolute_margin_cap, bool) or not isinstance(
            absolute_margin_cap, Real
        ):
            raise TypeError("absolute_margin_cap must be a real number or None")
        absolute_cap = float(absolute_margin_cap)
        if not isfinite(absolute_cap) or absolute_cap < 0.0:
            raise ValueError(
                "absolute_margin_cap must be finite and non-negative"
            )

    summary = gap_simplex(values, k=k, flat_tolerance=flat_tolerance)
    top_value = summary.sorted_logits[0]
    ratio = exp(values[candidate_index] - top_value)
    try:
        rank = summary.top_indices.index(candidate_index) + 1
    except ValueError:
        full_order = sorted(
            range(len(values)), key=lambda index: (-values[index], index)
        )
        return MarginDiagnostic(
            accepted=False,
            candidate_index=candidate_index,
            rank=full_order.index(candidate_index) + 1,
            normalized_loss=None,
            exact_probability_ratio=ratio,
            certified_ratio_lower_bound=None,
            reason="candidate is outside the selected top-k set",
        )
    if summary.degenerate:
        return MarginDiagnostic(
            accepted=False,
            candidate_index=candidate_index,
            rank=rank,
            normalized_loss=None,
            exact_probability_ratio=ratio,
            certified_ratio_lower_bound=None,
            reason="normalized margin is undefined for a flat top-k spectrum",
        )

    normalized_loss = summary.normalized_loss(rank)
    absolute_margin = top_value - values[candidate_index]
    normalized_ok = normalized_loss <= threshold
    absolute_ok = absolute_cap is None or absolute_margin <= absolute_cap
    accepted = normalized_ok and absolute_ok
    certified_margin = threshold * summary.spread
    if absolute_cap is not None:
        certified_margin = min(certified_margin, absolute_cap)
    lower_bound = exp(-certified_margin) if accepted else None
    if accepted:
        reason = "diagnostic conditions satisfied"
    elif not normalized_ok:
        reason = "normalized margin exceeds rho"
    else:
        reason = "absolute margin exceeds absolute_margin_cap"
    return MarginDiagnostic(
        accepted=accepted,
        candidate_index=candidate_index,
        rank=rank,
        normalized_loss=normalized_loss,
        exact_probability_ratio=ratio,
        certified_ratio_lower_bound=lower_bound,
        reason=reason,
    )


def conditional_accepted_distribution(
    proposal_probabilities: Sequence[Real],
    acceptance_probabilities: Sequence[Real],
) -> tuple[float, ...]:
    """Return ``q(x)a(x) / sum q a`` for accepted proposal samples.

    This elementary identity makes the consequence of a heuristic acceptance
    rule explicit: equality with a target distribution requires a correction
    involving the proposal distribution, not target ranks alone.
    """

    if len(proposal_probabilities) != len(acceptance_probabilities):
        raise ValueError("proposal and acceptance vectors must have equal length")
    if len(proposal_probabilities) < 2:
        raise ValueError("at least two outcomes are required")

    proposal: list[float] = []
    acceptance: list[float] = []
    for name, source, destination in (
        ("proposal", proposal_probabilities, proposal),
        ("acceptance", acceptance_probabilities, acceptance),
    ):
        for position, value in enumerate(source):
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} value at position {position} is not real")
            converted = float(value)
            if not isfinite(converted) or converted < 0.0:
                raise ValueError(f"{name} values must be finite and non-negative")
            if name == "acceptance" and converted > 1.0:
                raise ValueError("acceptance probabilities cannot exceed one")
            destination.append(converted)
    if not isclose(sum(proposal), 1.0, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError("proposal probabilities must sum to one")

    weights = [q_value * a_value for q_value, a_value in zip(proposal, acceptance, strict=True)]
    normalizer = sum(weights)
    if normalizer <= 0.0:
        raise ValueError("the rule never accepts a proposal")
    return tuple(weight / normalizer for weight in weights)
