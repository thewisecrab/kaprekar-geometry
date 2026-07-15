"""Leakage-resistant empirical benchmark for logit-spectrum hypotheses.

This module is an optional NumPy surface.  It requires independent training,
calibration, and test files and deliberately compares KGS features with an
information-matched raw-top-k baseline.  The output is evidence about the
supplied data only; it is not a universal reliability certificate.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - exercised only without the optional extra
    raise ImportError(
        "kaprekar.benchmark requires NumPy; install the project with the benchmark extra"
    ) from exc


SCHEMA_VERSION = "1.1"


@dataclass(frozen=True, slots=True)
class BenchmarkSplit:
    """Validated arrays for one independent benchmark partition."""

    logits: np.ndarray
    labels: np.ndarray
    sample_ids: np.ndarray
    group_ids: np.ndarray
    hidden: np.ndarray | None
    source: Path
    sha256: str

    @property
    def samples(self) -> int:
        return int(self.logits.shape[0])

    @property
    def vocabulary_size(self) -> int:
        return int(self.logits.shape[1])


@dataclass(frozen=True, slots=True)
class _Standardizer:
    mean: np.ndarray
    scale: np.ndarray

    def transform(self, values: np.ndarray) -> np.ndarray:
        return (values - self.mean) / self.scale


@dataclass(frozen=True, slots=True)
class _LogisticModel:
    coefficients: np.ndarray
    iterations: int
    gradient_inf_norm: float

    def decision_function(self, values: np.ndarray) -> np.ndarray:
        design = np.column_stack((np.ones(values.shape[0]), values))
        return design @ self.coefficients

    def predict_proba(self, values: np.ndarray) -> np.ndarray:
        return _sigmoid(self.decision_function(values))


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_split(path: str | Path) -> BenchmarkSplit:
    """Load a safe ``.npz`` split with row IDs and dependency-group IDs."""

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() != ".npz":
        raise ValueError("benchmark splits must be .npz files")

    with np.load(source, allow_pickle=False) as archive:
        required = {"logits", "labels", "sample_ids", "group_ids"}
        missing = required.difference(archive.files)
        if missing:
            missing_names = ", ".join(sorted(missing))
            raise ValueError(f"{source.name} is missing arrays: {missing_names}")
        logits = np.asarray(archive["logits"], dtype=np.float64)
        labels = np.asarray(archive["labels"])
        sample_ids = np.asarray(archive["sample_ids"])
        group_ids = np.asarray(archive["group_ids"])
        hidden = (
            np.asarray(archive["hidden"], dtype=np.float64)
            if "hidden" in archive.files
            else None
        )

    if logits.ndim != 2 or logits.shape[0] < 2 or logits.shape[1] < 2:
        raise ValueError("logits must have shape [samples>=2, vocabulary>=2]")
    if not np.isfinite(logits).all():
        raise ValueError("logits must contain only finite values")
    if labels.ndim != 1 or labels.shape[0] != logits.shape[0]:
        raise ValueError("labels must be a one-dimensional array aligned with logits")
    if not np.isin(labels, (0, 1)).all():
        raise ValueError("labels must be binary values 0 or 1")
    labels = labels.astype(np.float64, copy=False)
    if np.unique(labels).size != 2:
        raise ValueError("each split must contain both label classes")
    if sample_ids.ndim != 1 or sample_ids.shape[0] != logits.shape[0]:
        raise ValueError("sample_ids must be one-dimensional and aligned with logits")
    if sample_ids.dtype.kind not in {"U", "S", "i", "u"}:
        raise ValueError("sample_ids must be non-object strings or integers")
    sample_ids = sample_ids.astype(str)
    if np.unique(sample_ids).size != sample_ids.size:
        raise ValueError("sample_ids must be unique within each split")
    if group_ids.ndim != 1 or group_ids.shape[0] != logits.shape[0]:
        raise ValueError("group_ids must be one-dimensional and aligned with logits")
    if group_ids.dtype.kind not in {"U", "S", "i", "u"}:
        raise ValueError("group_ids must be non-object strings or integers")
    group_ids = group_ids.astype(str)
    if np.unique(group_ids).size < 2:
        raise ValueError("each split must contain at least two dependency groups")
    if hidden is not None:
        if hidden.ndim != 2 or hidden.shape[0] != logits.shape[0]:
            raise ValueError("hidden must have shape [samples, hidden_features]")
        if hidden.shape[1] < 1 or not np.isfinite(hidden).all():
            raise ValueError("hidden features must be non-empty and finite")

    return BenchmarkSplit(
        logits=logits,
        labels=labels,
        sample_ids=sample_ids,
        group_ids=group_ids,
        hidden=hidden,
        source=source,
        sha256=_file_sha256(source),
    )


def _validate_splits(
    train: BenchmarkSplit,
    calibration: BenchmarkSplit,
    test: BenchmarkSplit,
    k: int,
) -> None:
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")
    vocabulary_sizes = {split.vocabulary_size for split in (train, calibration, test)}
    if len(vocabulary_sizes) != 1:
        raise ValueError("all splits must use the same vocabulary dimension")
    vocabulary_size = vocabulary_sizes.pop()
    if not 2 <= k <= vocabulary_size:
        raise ValueError(f"k must be in [2, {vocabulary_size}]")

    names = (("train", train), ("calibration", calibration), ("test", test))
    for left_index, (left_name, left) in enumerate(names):
        for right_name, right in names[left_index + 1 :]:
            overlap = np.intersect1d(left.sample_ids, right.sample_ids)
            if overlap.size:
                preview = ", ".join(overlap[:3].tolist())
                raise ValueError(
                    f"sample leakage between {left_name} and {right_name}: {preview}"
                )
            group_overlap = np.intersect1d(left.group_ids, right.group_ids)
            if group_overlap.size:
                preview = ", ".join(group_overlap[:3].tolist())
                raise ValueError(
                    f"group leakage between {left_name} and {right_name}: {preview}"
                )

    hidden_dimensions = {
        split.hidden.shape[1] for split in (train, calibration, test) if split.hidden is not None
    }
    hidden_presence = [split.hidden is not None for split in (train, calibration, test)]
    if any(hidden_presence) and not all(hidden_presence):
        raise ValueError("hidden features must be present in all three splits or none")
    if len(hidden_dimensions) > 1:
        raise ValueError("hidden feature dimensions must match across splits")


def _logsumexp(values: np.ndarray, axis: int) -> np.ndarray:
    maximum = np.max(values, axis=axis, keepdims=True)
    return np.squeeze(maximum, axis=axis) + np.log(
        np.sum(np.exp(values - maximum), axis=axis)
    )


def feature_families(
    split: BenchmarkSplit,
    k: int,
    *,
    flat_tolerance: float = 1e-12,
) -> dict[str, np.ndarray]:
    """Construct baselines and KGS ablations from one split."""

    if not isinstance(split, BenchmarkSplit):
        raise TypeError("split must be a BenchmarkSplit")
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")
    if not 2 <= k <= split.vocabulary_size:
        raise ValueError(f"k must be in [2, {split.vocabulary_size}]")
    if isinstance(flat_tolerance, (bool, np.bool_)) or not isinstance(
        flat_tolerance, (int, float, np.integer, np.floating)
    ):
        raise TypeError("flat_tolerance must be a real number")
    if not np.isfinite(flat_tolerance) or flat_tolerance < 0.0:
        raise ValueError("flat_tolerance must be finite and non-negative")
    logits = split.logits
    order = np.argsort(-logits, axis=1, kind="stable")[:, :k]
    top = np.take_along_axis(logits, order, axis=1)
    spread = top[:, 0] - top[:, -1]
    if not np.isfinite(spread).all():
        raise ValueError("top-k spread overflowed; rescale logits before benchmarking")
    gaps = top[:, :-1] - top[:, 1:]
    degenerate = spread <= flat_tolerance
    coordinates = np.divide(
        gaps,
        spread[:, None],
        out=np.zeros_like(gaps),
        where=~degenerate[:, None],
    )

    log_partition = _logsumexp(logits, axis=1)
    with np.errstate(over="ignore"):
        log_probabilities = logits - log_partition[:, None]
    probabilities = np.exp(log_probabilities)
    max_probability = np.max(probabilities, axis=1)[:, None]
    entropy_terms = np.zeros_like(probabilities)
    np.multiply(
        probabilities,
        log_probabilities,
        out=entropy_terms,
        where=probabilities > 0.0,
    )
    entropy = -np.sum(entropy_terms, axis=1)[:, None]
    margin = (top[:, 0] - top[:, 1])[:, None]
    sorted_top_k_probabilities = np.take_along_axis(
        probabilities, order, axis=1
    )
    top_k_mass = sorted_top_k_probabilities.sum(axis=1)[:, None]
    centered_top = top[:, :-1] - top[:, -1, None]

    # Drop the final simplex coordinate to remove the exact sum-to-one
    # collinearity. The degeneracy mask preserves the flat-spectrum stratum.
    kgs = np.column_stack(
        (
            np.log1p(spread),
            coordinates[:, :-1],
            degenerate.astype(np.float64),
        )
    )
    output_hybrid = np.column_stack(
        (kgs, max_probability, -entropy, margin, top_k_mass)
    )
    raw_top_k = np.column_stack(
        (centered_top, degenerate.astype(np.float64))
    )

    families = {
        "max_probability": max_probability,
        "negative_entropy": -entropy,
        "top1_margin": margin,
        "raw_sorted_top_k": raw_top_k,
        "sorted_top_k_probabilities": sorted_top_k_probabilities,
        "kgs": kgs,
        "output_hybrid": output_hybrid,
    }
    if split.hidden is not None:
        families["output_plus_hidden"] = np.column_stack(
            (output_hybrid, split.hidden)
        )
    return families


def _fit_standardizer(values: np.ndarray) -> _Standardizer:
    mean = values.mean(axis=0)
    scale = values.std(axis=0)
    scale = np.where(scale > np.finfo(np.float64).eps, scale, 1.0)
    return _Standardizer(mean=mean, scale=scale)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    output = np.empty_like(values, dtype=np.float64)
    positive = values >= 0.0
    output[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    negative_exp = np.exp(values[~positive])
    output[~positive] = negative_exp / (1.0 + negative_exp)
    return output


def _fit_logistic(
    values: np.ndarray,
    labels: np.ndarray,
    *,
    regularization: float,
    max_iterations: int = 200,
    tolerance: float = 1e-9,
) -> _LogisticModel:
    if (
        isinstance(regularization, (bool, np.bool_))
        or not np.isfinite(regularization)
        or regularization <= 0.0
    ):
        raise ValueError("regularization must be finite and strictly positive")
    design = np.column_stack((np.ones(values.shape[0]), values))
    coefficients = np.zeros(design.shape[1], dtype=np.float64)
    penalty = np.eye(design.shape[1], dtype=np.float64) * regularization
    penalty[0, 0] = 0.0

    converged = False
    iteration = 0
    for iteration in range(1, max_iterations + 1):
        probabilities = _sigmoid(design @ coefficients)
        weights = np.clip(probabilities * (1.0 - probabilities), 1e-9, None)
        gradient = design.T @ (probabilities - labels) + penalty @ coefficients
        hessian = (design.T * weights) @ design + penalty
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        if not np.isfinite(step).all():
            raise RuntimeError("logistic fit produced a non-finite Newton step")
        coefficients -= step
        if not np.isfinite(coefficients).all():
            raise RuntimeError("logistic fit produced non-finite coefficients")
        if np.linalg.norm(step, ord=np.inf) <= tolerance:
            converged = True
            break
    if not converged:
        raise RuntimeError(
            f"logistic fit did not converge in {max_iterations} iterations"
        )
    final_probabilities = _sigmoid(design @ coefficients)
    final_gradient = (
        design.T @ (final_probabilities - labels) + penalty @ coefficients
    )
    return _LogisticModel(
        coefficients=coefficients,
        iterations=iteration,
        gradient_inf_norm=float(np.linalg.norm(final_gradient, ord=np.inf)),
    )


def _fit_platt(scores: np.ndarray, labels: np.ndarray) -> _LogisticModel:
    values = scores.reshape(-1, 1)
    return _fit_logistic(values, labels, regularization=1e-6)


def _average_rank(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="stable")
    sorted_values = values[order]
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = (start + 1 + end) / 2.0
        start = end
    return ranks


def _auroc(labels: np.ndarray, scores: np.ndarray) -> float:
    positives = labels == 1.0
    positive_count = int(positives.sum())
    negative_count = labels.size - positive_count
    ranks = _average_rank(scores)
    return float(
        (ranks[positives].sum() - positive_count * (positive_count + 1) / 2.0)
        / (positive_count * negative_count)
    )


def _average_precision(labels: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores, kind="stable")
    sorted_scores = scores[order]
    sorted_labels = labels[order]
    total_positives = float(labels.sum())
    true_positives = 0.0
    seen = 0
    previous_recall = 0.0
    area = 0.0
    start = 0
    while start < labels.size:
        end = start + 1
        while end < labels.size and sorted_scores[end] == sorted_scores[start]:
            end += 1
        true_positives += float(sorted_labels[start:end].sum())
        seen = end
        recall = true_positives / total_positives
        precision = true_positives / seen
        area += (recall - previous_recall) * precision
        previous_recall = recall
        start = end
    return area


def binary_metrics(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    ece_bins: int = 15,
    target_risk: float = 0.10,
) -> dict[str, float]:
    """Compute discrimination, calibration, and selective-risk metrics."""

    labels = np.asarray(labels, dtype=np.float64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if labels.ndim != 1 or probabilities.shape != labels.shape:
        raise ValueError(
            "labels and probabilities must be aligned one-dimensional arrays"
        )
    if not np.isin(labels, (0.0, 1.0)).all() or np.unique(labels).size != 2:
        raise ValueError("labels must contain both binary classes")
    if not np.isfinite(probabilities).all() or np.any(
        (probabilities < 0.0) | (probabilities > 1.0)
    ):
        raise ValueError("probabilities must be finite and in [0, 1]")
    if not isinstance(ece_bins, int) or isinstance(ece_bins, bool) or ece_bins < 2:
        raise ValueError("ece_bins must be an integer >= 2")
    if isinstance(target_risk, (bool, np.bool_)) or not isinstance(
        target_risk, (int, float, np.integer, np.floating)
    ):
        raise TypeError("target_risk must be a real number")
    target_risk = float(target_risk)
    if not np.isfinite(target_risk) or not 0.0 <= target_risk <= 1.0:
        raise ValueError("target_risk must be in [0, 1]")

    clipped = np.clip(probabilities, 1e-12, 1.0 - 1e-12)
    brier = float(np.mean((probabilities - labels) ** 2))
    nll = float(
        -np.mean(
            labels * np.log(clipped)
            + (1.0 - labels) * np.log1p(-clipped)
        )
    )

    bin_count = min(ece_bins, labels.size)
    quantiles = np.linspace(0.0, 1.0, bin_count + 1)[1:-1]
    edges = np.quantile(probabilities, quantiles, method="linear")
    bin_assignments = np.searchsorted(edges, probabilities, side="right")
    ece = 0.0
    for bin_index in range(bin_count):
        bin_indices = np.flatnonzero(bin_assignments == bin_index)
        if bin_indices.size:
            ece += (bin_indices.size / labels.size) * abs(
                float(labels[bin_indices].mean() - probabilities[bin_indices].mean())
            )

    selective_order = np.argsort(-probabilities, kind="stable")
    sorted_probabilities = probabilities[selective_order]
    sorted_errors = 1.0 - labels[selective_order]
    cumulative_errors = 0.0
    previous_end = 0
    aurc = 0.0
    coverage_at_risk = 0.0
    start = 0
    while start < labels.size:
        end = start + 1
        while (
            end < labels.size
            and sorted_probabilities[end] == sorted_probabilities[start]
        ):
            end += 1
        cumulative_errors += float(sorted_errors[start:end].sum())
        risk = cumulative_errors / end
        coverage = end / labels.size
        aurc += ((end - previous_end) / labels.size) * risk
        if risk <= target_risk:
            coverage_at_risk = coverage
        previous_end = end
        start = end

    return {
        "auroc": _auroc(labels, probabilities),
        "average_precision": _average_precision(labels, probabilities),
        "brier": brier,
        "negative_log_likelihood": nll,
        "ece_equal_frequency": ece,
        "aurc": aurc,
        "empirical_coverage_at_target_risk": coverage_at_risk,
        "target_risk": float(target_risk),
    }


def bootstrap_metric_intervals(
    labels: np.ndarray,
    probabilities: np.ndarray,
    *,
    group_ids: np.ndarray,
    replicates: int = 500,
    confidence_level: float = 0.95,
    seed: int = 0x6174,
    ece_bins: int = 15,
    target_risk: float = 0.10,
) -> dict[str, dict[str, float | int | str]]:
    """Return deterministic dependency-group bootstrap intervals."""

    if (
        not isinstance(replicates, int)
        or isinstance(replicates, bool)
        or replicates < 1
    ):
        raise ValueError("replicates must be an integer >= 1")
    if isinstance(confidence_level, (bool, np.bool_)) or not isinstance(
        confidence_level, (int, float, np.integer, np.floating)
    ):
        raise TypeError("confidence_level must be a real number")
    confidence_level = float(confidence_level)
    if not np.isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must be strictly between zero and one")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")

    labels = np.asarray(labels, dtype=np.float64)
    probabilities = np.asarray(probabilities, dtype=np.float64)
    # Reuse the complete input validation from the point estimator.
    point = binary_metrics(
        labels,
        probabilities,
        ece_bins=ece_bins,
        target_risk=target_risk,
    )
    groups = np.asarray(group_ids)
    if groups.ndim != 1 or groups.shape[0] != labels.size:
        raise ValueError("group_ids must be one-dimensional and aligned")
    if groups.dtype.kind not in {"U", "S", "i", "u"}:
        raise ValueError("group_ids must be non-object strings or integers")
    groups = groups.astype(str)
    unique_groups, inverse = np.unique(groups, return_inverse=True)
    if unique_groups.size < 2:
        raise ValueError("bootstrap requires at least two dependency groups")
    group_members = tuple(
        np.flatnonzero(inverse == group_index)
        for group_index in range(unique_groups.size)
    )
    metric_names = tuple(name for name in point if name != "target_risk")
    samples = {name: [] for name in metric_names}
    rng = np.random.default_rng(seed)
    completed = 0
    attempts = 0
    maximum_attempts = max(replicates * 20, 100)
    while completed < replicates and attempts < maximum_attempts:
        attempts += 1
        sampled_groups = rng.integers(
            0,
            unique_groups.size,
            size=unique_groups.size,
        )
        indices = np.concatenate(
            [group_members[group_index] for group_index in sampled_groups]
        )
        sampled_labels = labels[indices]
        if np.unique(sampled_labels).size != 2:
            continue
        metrics = binary_metrics(
            sampled_labels,
            probabilities[indices],
            ece_bins=ece_bins,
            target_risk=target_risk,
        )
        for name in metric_names:
            samples[name].append(metrics[name])
        completed += 1
    if completed < replicates:
        raise ValueError("unable to draw bootstrap samples containing both label classes")

    tail = (1.0 - confidence_level) / 2.0
    return {
        name: {
            "lower": float(np.quantile(values, tail)),
            "upper": float(np.quantile(values, 1.0 - tail)),
            "confidence_level": confidence_level,
            "replicates": replicates,
            "resampling_unit": "dependency_group",
            "group_count": int(unique_groups.size),
        }
        for name, values in samples.items()
    }


def run_benchmark(
    train_path: str | Path,
    calibration_path: str | Path,
    test_path: str | Path,
    *,
    k: int = 10,
    regularization: float = 1.0,
    ece_bins: int = 15,
    target_risk: float = 0.10,
    flat_tolerance: float = 1e-12,
    bootstrap_replicates: int = 500,
    bootstrap_confidence: float = 0.95,
    bootstrap_seed: int = 0x6174,
) -> dict[str, Any]:
    """Fit, calibrate, and evaluate all feature families on untouched test data."""

    if isinstance(regularization, (bool, np.bool_)) or not isinstance(
        regularization, (int, float, np.integer, np.floating)
    ):
        raise TypeError("regularization must be a real number")
    regularization = float(regularization)
    if not np.isfinite(regularization) or regularization <= 0.0:
        raise ValueError("regularization must be finite and strictly positive")

    train = load_split(train_path)
    calibration = load_split(calibration_path)
    test = load_split(test_path)
    _validate_splits(train, calibration, test, k)

    train_features = feature_families(train, k, flat_tolerance=flat_tolerance)
    calibration_features = feature_families(
        calibration, k, flat_tolerance=flat_tolerance
    )
    test_features = feature_families(test, k, flat_tolerance=flat_tolerance)
    if (
        train_features.keys() != calibration_features.keys()
        or train_features.keys() != test_features.keys()
    ):
        raise ValueError("feature families differ across splits")

    model_results: dict[str, Any] = {}
    for name in train_features:
        standardizer = _fit_standardizer(train_features[name])
        standardized_train = standardizer.transform(train_features[name])
        standardized_calibration = standardizer.transform(calibration_features[name])
        standardized_test = standardizer.transform(test_features[name])

        predictor = _fit_logistic(
            standardized_train,
            train.labels,
            regularization=regularization,
        )
        calibration_scores = predictor.decision_function(standardized_calibration)
        calibrator = _fit_platt(calibration_scores, calibration.labels)
        test_scores = predictor.decision_function(standardized_test)
        test_probabilities = calibrator.predict_proba(test_scores.reshape(-1, 1))
        model_results[name] = {
            "feature_count": int(train_features[name].shape[1]),
            "fit_diagnostics": {
                "predictor_iterations": predictor.iterations,
                "predictor_gradient_inf_norm": predictor.gradient_inf_norm,
                "calibrator_iterations": calibrator.iterations,
                "calibrator_gradient_inf_norm": calibrator.gradient_inf_norm,
                "status": "converged",
            },
            "metrics": binary_metrics(
                test.labels,
                test_probabilities,
                ece_bins=ece_bins,
                target_risk=target_risk,
            ),
            "bootstrap_intervals": bootstrap_metric_intervals(
                test.labels,
                test_probabilities,
                group_ids=test.group_ids,
                replicates=bootstrap_replicates,
                confidence_level=bootstrap_confidence,
                seed=bootstrap_seed,
                ece_bins=ece_bins,
                target_risk=target_risk,
            ),
            "test_probabilities": test_probabilities.tolist(),
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_scope": "empirical_on_supplied_independent_splits_not_universal",
        "configuration": {
            "k": k,
            "regularization": regularization,
            "ece_bins": ece_bins,
            "target_risk": target_risk,
            "flat_tolerance": flat_tolerance,
            "bootstrap_replicates": bootstrap_replicates,
            "bootstrap_confidence": bootstrap_confidence,
            "bootstrap_seed": bootstrap_seed,
        },
        "splits": {
            name: {
                "path": str(split.source),
                "sha256": split.sha256,
                "samples": split.samples,
                "dependency_groups": int(np.unique(split.group_ids).size),
                "vocabulary_size": split.vocabulary_size,
                "positive_rate": float(split.labels.mean()),
            }
            for name, split in (
                ("train", train),
                ("calibration", calibration),
                ("test", test),
            )
        },
        "test_sample_ids": test.sample_ids.tolist(),
        "test_group_ids": test.group_ids.tolist(),
        "models": model_results,
    }
