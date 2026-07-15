"""Finite-sample calibration for confidence-based selective prediction.

This is deliberately not branded as conformal prediction. It uses exact
one-sided binomial bounds on a fixed threshold grid with a Bonferroni correction
for adaptive threshold selection. The guarantee requires an untouched,
IID risk-calibration sample from the deployment law and a score function fixed
before that sample is observed. Generic exchangeability alone is not enough
for a Clopper-Pearson guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, lgamma, log, log1p
from numbers import Integral, Real
from typing import Sequence


@dataclass(frozen=True, slots=True)
class SelectiveRiskCalibration:
    """Result of finite-sample selective-risk threshold calibration."""

    status: str
    threshold: float | None
    target_risk: float
    confidence_level: float
    calibration_accepted: int
    calibration_total: int
    calibration_errors: int
    calibration_coverage: float
    empirical_risk: float | None
    risk_upper_bound: float | None
    threshold_count: int
    per_threshold_alpha: float
    assumption: str

    def to_dict(self) -> dict[str, int | float | str | None]:
        return {
            "status": self.status,
            "threshold": self.threshold,
            "target_risk": self.target_risk,
            "confidence_level": self.confidence_level,
            "calibration_accepted": self.calibration_accepted,
            "calibration_total": self.calibration_total,
            "calibration_errors": self.calibration_errors,
            "calibration_coverage": self.calibration_coverage,
            "empirical_risk": self.empirical_risk,
            "risk_upper_bound": self.risk_upper_bound,
            "threshold_count": self.threshold_count,
            "per_threshold_alpha": self.per_threshold_alpha,
            "assumption": self.assumption,
        }


def _require_probability(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    converted = float(value)
    if not isfinite(converted) or not 0.0 <= converted <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return converted


def _logsumexp(values: Sequence[float]) -> float:
    maximum = max(values)
    return maximum + log(sum(exp(value - maximum) for value in values))


def _binomial_cdf(errors: int, trials: int, probability: float) -> float:
    if probability <= 0.0:
        return 1.0
    if probability >= 1.0:
        return 1.0 if errors == trials else 0.0
    log_probability = log(probability)
    log_complement = log1p(-probability)
    log_terms = [
        lgamma(trials + 1)
        - lgamma(successes + 1)
        - lgamma(trials - successes + 1)
        + successes * log_probability
        + (trials - successes) * log_complement
        for successes in range(errors + 1)
    ]
    return exp(_logsumexp(log_terms))


def clopper_pearson_upper(
    errors: int,
    trials: int,
    *,
    alpha: float = 0.05,
) -> float:
    """Return the exact one-sided Clopper-Pearson upper error-rate bound."""

    if isinstance(errors, bool) or not isinstance(errors, Integral):
        raise TypeError("errors must be an integer")
    if isinstance(trials, bool) or not isinstance(trials, Integral):
        raise TypeError("trials must be an integer")
    errors = int(errors)
    trials = int(trials)
    if trials < 1:
        raise ValueError("trials must be at least one")
    if not 0 <= errors <= trials:
        raise ValueError("errors must be in [0, trials]")
    tail = _require_probability("alpha", alpha)
    if tail in {0.0, 1.0}:
        raise ValueError("alpha must be strictly between zero and one")
    if errors == trials:
        return 1.0

    lower = 0.0
    upper = 1.0
    for _ in range(80):
        midpoint = (lower + upper) / 2.0
        if _binomial_cdf(errors, trials, midpoint) > tail:
            lower = midpoint
        else:
            upper = midpoint
    return upper


def calibrate_selective_risk(
    confidences: Sequence[Real],
    correctness: Sequence[int | bool],
    *,
    target_risk: float,
    confidence_level: float = 0.95,
    threshold_count: int = 101,
    min_accepted: int = 30,
) -> SelectiveRiskCalibration:
    """Choose the highest-coverage threshold with a simultaneous risk bound.

    Thresholds are fixed to an evenly spaced grid before labels are examined.
    One-sided exact binomial bounds are Bonferroni-adjusted across that grid, so
    the selected bound is simultaneous. This does not protect against dataset
    shift or reuse of the calibration sample for training or score calibration.
    """

    if len(confidences) != len(correctness):
        raise ValueError("confidences and correctness must have equal length")
    if len(confidences) < 2:
        raise ValueError("at least two calibration examples are required")
    scores = tuple(
        _require_probability(f"confidences[{index}]", value)
        for index, value in enumerate(confidences)
    )
    labels: list[int] = []
    for index, value in enumerate(correctness):
        if isinstance(value, bool):
            labels.append(int(value))
        elif isinstance(value, Integral) and int(value) in {0, 1}:
            labels.append(int(value))
        else:
            raise ValueError(f"correctness[{index}] must be 0, 1, or bool")

    target = _require_probability("target_risk", target_risk)
    confidence = _require_probability("confidence_level", confidence_level)
    if confidence in {0.0, 1.0}:
        raise ValueError("confidence_level must be strictly between zero and one")
    if isinstance(threshold_count, bool) or not isinstance(threshold_count, Integral):
        raise TypeError("threshold_count must be an integer")
    threshold_count = int(threshold_count)
    if threshold_count < 2:
        raise ValueError("threshold_count must be at least two")
    if isinstance(min_accepted, bool) or not isinstance(min_accepted, Integral):
        raise TypeError("min_accepted must be an integer")
    min_accepted = int(min_accepted)
    if not 1 <= min_accepted <= len(scores):
        raise ValueError("min_accepted must be in [1, sample size]")

    per_threshold_alpha = (1.0 - confidence) / threshold_count
    best: tuple[int, float, int, float] | None = None
    for step in range(threshold_count):
        threshold = step / (threshold_count - 1)
        selected = [index for index, score in enumerate(scores) if score >= threshold]
        accepted = len(selected)
        if accepted < min_accepted:
            continue
        errors = sum(1 - labels[index] for index in selected)
        upper = clopper_pearson_upper(
            errors,
            accepted,
            alpha=per_threshold_alpha,
        )
        if upper <= target and (best is None or accepted > best[0]):
            best = (accepted, threshold, errors, upper)

    assumption = (
        "score fixed before an untouched IID risk-calibration set sampled from "
        "the deployment law; generic exchangeability is insufficient; "
        "no guarantee under arbitrary distribution shift"
    )
    if best is None:
        return SelectiveRiskCalibration(
            status="no_safe_threshold",
            threshold=None,
            target_risk=target,
            confidence_level=confidence,
            calibration_accepted=0,
            calibration_total=len(scores),
            calibration_errors=0,
            calibration_coverage=0.0,
            empirical_risk=None,
            risk_upper_bound=None,
            threshold_count=threshold_count,
            per_threshold_alpha=per_threshold_alpha,
            assumption=assumption,
        )

    accepted, threshold, errors, upper = best
    return SelectiveRiskCalibration(
        status="calibrated",
        threshold=threshold,
        target_risk=target,
        confidence_level=confidence,
        calibration_accepted=accepted,
        calibration_total=len(scores),
        calibration_errors=errors,
        calibration_coverage=accepted / len(scores),
        empirical_risk=errors / accepted,
        risk_upper_bound=upper,
        threshold_count=threshold_count,
        per_threshold_alpha=per_threshold_alpha,
        assumption=assumption,
    )


def apply_abstention(
    confidences: Sequence[Real],
    calibration: SelectiveRiskCalibration,
) -> tuple[bool, ...]:
    """Return trust decisions for a successfully calibrated threshold."""

    if not isinstance(calibration, SelectiveRiskCalibration):
        raise TypeError("calibration must be a SelectiveRiskCalibration")
    if calibration.threshold is None:
        raise ValueError("no safe threshold was calibrated")
    return tuple(
        _require_probability(f"confidences[{index}]", value)
        >= calibration.threshold
        for index, value in enumerate(confidences)
    )


__all__ = [
    "SelectiveRiskCalibration",
    "apply_abstention",
    "calibrate_selective_risk",
    "clopper_pearson_upper",
]
