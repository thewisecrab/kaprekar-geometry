"""Command-line interface for exact Kaprekar analysis and verification."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .core import ComputationLimitError, digit_multiset_count, spectrum_count
from .dynamics import (
    DEFAULT_DYNAMICS_DIGIT_LIMIT,
    DEFAULT_DYNAMICS_WORK_UNIT_LIMIT,
    DEFAULT_MULTISET_LIMIT,
    DEFAULT_SPECTRUM_LIMIT,
    analyze_functional_graph,
    fixed_spectra,
    raw_spectrum_weights,
)
from .logits import gap_simplex, tail_mass_bounds
from .verification import (
    DEFAULT_CASE_LIMIT,
    DEFAULT_DIGIT_LIMIT,
    DEFAULT_SAMPLE_SEED,
    DEFAULT_SAMPLE_SIZE,
    DEFAULT_STATE_LIMIT,
    DEFAULT_WORK_UNIT_LIMIT,
    verify_ranges,
)


def _json_dump(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _add_base_digits(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base", "-b", type=int, required=True)
    parser.add_argument("--digits", "-n", type=int, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaprekar",
        description="Exact generalized Kaprekar spectrum analysis",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify = subparsers.add_parser(
        "verify", help="verify factorization and image-cardinality claims"
    )
    verify.add_argument("--base-min", type=int, default=2)
    verify.add_argument("--base-max", type=int, default=8)
    verify.add_argument("--digits-min", type=int, default=1)
    verify.add_argument("--digits-max", type=int, default=7)
    verify.add_argument(
        "--mode",
        choices=("exhaustive", "reduced", "sampled"),
        default="exhaustive",
    )
    verify.add_argument("--samples", type=int, default=DEFAULT_SAMPLE_SIZE)
    verify.add_argument("--seed", type=int, default=DEFAULT_SAMPLE_SEED)
    verify.add_argument("--max-states", type=int, default=DEFAULT_STATE_LIMIT)
    verify.add_argument(
        "--max-work-units", type=int, default=DEFAULT_WORK_UNIT_LIMIT
    )
    verify.add_argument("--max-cases", type=int, default=DEFAULT_CASE_LIMIT)
    verify.add_argument("--max-digits", type=int, default=DEFAULT_DIGIT_LIMIT)
    verify.add_argument("--force", action="store_true")
    verify.add_argument("--json", action="store_true")

    fixed = subparsers.add_parser("fixed", help="list exact fixed spectra")
    _add_base_digits(fixed)
    fixed.add_argument("--include-zero", action="store_true")
    fixed.add_argument("--max-spectra", type=int, default=DEFAULT_SPECTRUM_LIMIT)
    fixed.add_argument(
        "--max-work-units",
        type=int,
        default=DEFAULT_DYNAMICS_WORK_UNIT_LIMIT,
    )
    fixed.add_argument(
        "--max-digits",
        type=int,
        default=DEFAULT_DYNAMICS_DIGIT_LIMIT,
    )
    fixed.add_argument("--force", action="store_true")
    fixed.add_argument("--json", action="store_true")

    analyze = subparsers.add_parser(
        "analyze", help="analyze the complete reduced functional graph"
    )
    _add_base_digits(analyze)
    analyze.add_argument("--no-raw-weights", action="store_true")
    analyze.add_argument("--include-states", action="store_true")
    analyze.add_argument("--max-spectra", type=int, default=DEFAULT_SPECTRUM_LIMIT)
    analyze.add_argument("--max-multisets", type=int, default=DEFAULT_MULTISET_LIMIT)
    analyze.add_argument(
        "--max-work-units",
        type=int,
        default=DEFAULT_DYNAMICS_WORK_UNIT_LIMIT,
    )
    analyze.add_argument(
        "--max-digits",
        type=int,
        default=DEFAULT_DYNAMICS_DIGIT_LIMIT,
    )
    analyze.add_argument("--force", action="store_true")
    analyze.add_argument("--json", action="store_true")

    weights = subparsers.add_parser(
        "weights", help="compute exact raw population per spectrum"
    )
    _add_base_digits(weights)
    weights.add_argument("--include-weights", action="store_true")
    weights.add_argument("--max-multisets", type=int, default=DEFAULT_MULTISET_LIMIT)
    weights.add_argument(
        "--max-work-units",
        type=int,
        default=DEFAULT_DYNAMICS_WORK_UNIT_LIMIT,
    )
    weights.add_argument(
        "--max-digits",
        type=int,
        default=DEFAULT_DYNAMICS_DIGIT_LIMIT,
    )
    weights.add_argument("--force", action="store_true")
    weights.add_argument("--json", action="store_true")

    logits = subparsers.add_parser(
        "logits", help="inspect normalized top-k logit geometry safely"
    )
    logits.add_argument("values", nargs="+", type=float)
    logits.add_argument("--top-k", type=int)
    logits.add_argument("--flat-tolerance", type=float, default=0.0)
    logits.add_argument("--json", action="store_true")

    benchmark = subparsers.add_parser(
        "benchmark",
        help="fit and evaluate matched logit baselines on independent NPZ splits",
    )
    benchmark.add_argument("--train", required=True)
    benchmark.add_argument("--calibration", required=True)
    benchmark.add_argument("--test", required=True)
    benchmark.add_argument("--top-k", type=int, default=10)
    benchmark.add_argument("--regularization", type=float, default=1.0)
    benchmark.add_argument("--ece-bins", type=int, default=15)
    benchmark.add_argument("--target-risk", type=float, default=0.10)
    benchmark.add_argument("--flat-tolerance", type=float, default=1e-12)
    benchmark.add_argument("--bootstrap-replicates", type=int, default=500)
    benchmark.add_argument("--bootstrap-confidence", type=float, default=0.95)
    benchmark.add_argument("--bootstrap-seed", type=int, default=0x6174)
    benchmark.add_argument("--summary-only", action="store_true")
    benchmark.set_defaults(json=True)
    return parser


def _run_verify(args: argparse.Namespace) -> int:
    report = verify_ranges(
        args.base_min,
        args.base_max,
        args.digits_min,
        args.digits_max,
        mode=args.mode,
        sample_size=args.samples,
        seed=args.seed,
        max_states=args.max_states,
        max_work_units=args.max_work_units,
        max_cases=args.max_cases,
        max_digits=args.max_digits,
        force=args.force,
    )
    if args.json:
        _json_dump(report.to_dict())
    else:
        status = "PASS" if report.passed else "FAIL"
        print(
            f"{status}: {len(report.cases)} {args.mode} cases, "
            f"{report.total_states_checked:,} states checked in "
            f"{report.duration_seconds:.3f}s"
        )
        for case in report.cases:
            image = (
                str(case.observed_image_size)
                if case.image_cardinality_verified
                else "not exhaustively verified"
            )
            print(
                f"  b={case.base} n={case.digits}: "
                f"checks={case.factorization_checks:,}, image={image}, "
                f"expected={case.expected_image_size}, "
                f"status={'PASS' if case.passed else 'FAIL'}"
            )
            for failure in case.failures:
                print(f"    {failure}")
    return 0 if report.passed else 1


def _run_fixed(args: argparse.Namespace) -> int:
    points = fixed_spectra(
        args.base,
        args.digits,
        include_zero=args.include_zero,
        max_spectra=args.max_spectra,
        max_work_units=args.max_work_units,
        max_digits=args.max_digits,
        force=args.force,
    )
    if args.json:
        _json_dump(
            {
                "base": args.base,
                "digits": args.digits,
                "include_zero": args.include_zero,
                "fixed": [
                    {"spectrum": list(spectrum), "value": value}
                    for spectrum, value in points
                ],
            }
        )
    else:
        print(f"Fixed spectra for base={args.base}, digits={args.digits}:")
        if not points:
            print("  none")
        for spectrum, value in points:
            print(f"  {spectrum} -> {value}")
    return 0


def _run_analyze(args: argparse.Namespace) -> int:
    analysis = analyze_functional_graph(
        args.base,
        args.digits,
        include_raw_weights=not args.no_raw_weights,
        max_spectra=args.max_spectra,
        max_multisets=args.max_multisets,
        max_work_units=args.max_work_units,
        max_digits=args.max_digits,
        force=args.force,
    )
    if args.json:
        _json_dump(analysis.to_dict(include_states=args.include_states))
    else:
        print(
            f"base={analysis.base}, digits={analysis.digits}: "
            f"{analysis.spectrum_state_count:,} spectra, "
            f"{len(analysis.attractors)} attractors"
        )
        for attractor in analysis.attractors:
            basin = (
                "unweighted"
                if attractor.raw_basin_size is None
                else f"raw basin={attractor.raw_basin_size:,}"
            )
            print(
                f"  attractor {attractor.attractor_id}: "
                f"cycle={attractor.cycle_values}, "
                f"reduced basin={attractor.reduced_basin_size:,}, {basin}, "
                f"max reduced depth={attractor.maximum_reduced_depth}"
            )
    return 0


def _run_weights(args: argparse.Namespace) -> int:
    weights = raw_spectrum_weights(
        args.base,
        args.digits,
        max_multisets=args.max_multisets,
        max_work_units=args.max_work_units,
        max_digits=args.max_digits,
        force=args.force,
    )
    payload: dict[str, object] = {
        "base": args.base,
        "digits": args.digits,
        "spectrum_count": spectrum_count(args.base, args.digits),
        "digit_multiset_count": digit_multiset_count(args.base, args.digits),
        "raw_state_count": args.base**args.digits,
        "weight_sum": sum(weights.values()),
    }
    if args.include_weights:
        payload["weights"] = [
            {"spectrum": list(spectrum), "weight": weight}
            for spectrum, weight in weights.items()
        ]
    if args.json:
        _json_dump(payload)
    else:
        print(
            f"base={args.base}, digits={args.digits}: "
            f"{payload['spectrum_count']:,} spectrum classes, "
            f"{payload['weight_sum']:,} raw states"
        )
        if args.include_weights:
            for item in payload["weights"]:  # type: ignore[union-attr]
                print(f"  {tuple(item['spectrum'])}: {item['weight']:,}")
    return 0


def _run_logits(args: argparse.Namespace) -> int:
    summary = gap_simplex(
        args.values,
        k=args.top_k,
        flat_tolerance=args.flat_tolerance,
    )
    bounds = tail_mass_bounds(summary, vocabulary_size=len(args.values))
    payload = {
        "vocabulary_size": len(args.values),
        "k": summary.k,
        "top_indices": list(summary.top_indices),
        "sorted_logits": list(summary.sorted_logits),
        "spread": summary.spread,
        "coordinates": (
            None if summary.coordinates is None else list(summary.coordinates)
        ),
        "shape_degrees_of_freedom": summary.shape_degrees_of_freedom,
        "degenerate": summary.degenerate,
        "full_distribution": {
            "top_k_probability_mass": summary.top_k_probability_mass,
            "max_probability": summary.max_probability,
            "entropy_nats": summary.entropy,
        },
        "bounds_from_top_k_only": {
            "top_k_mass_lower": bounds.top_k_mass_lower,
            "top_k_mass_upper": bounds.top_k_mass_upper,
            "top1_probability_lower": bounds.top1_probability_lower,
            "top1_probability_upper": bounds.top1_probability_upper,
        },
    }
    if args.json:
        _json_dump(payload)
    else:
        print(
            f"k={summary.k}, spread={summary.spread:g}, "
            f"degenerate={summary.degenerate}"
        )
        print(f"  top indices: {summary.top_indices}")
        print(f"  coordinates: {summary.coordinates}")
        print(
            f"  full entropy={summary.entropy:.6g} nats, "
            f"top-k mass={summary.top_k_probability_mass:.6g}"
        )
    return 0


def _run_benchmark(args: argparse.Namespace) -> int:
    from .benchmark import run_benchmark

    payload = run_benchmark(
        args.train,
        args.calibration,
        args.test,
        k=args.top_k,
        regularization=args.regularization,
        ece_bins=args.ece_bins,
        target_risk=args.target_risk,
        flat_tolerance=args.flat_tolerance,
        bootstrap_replicates=args.bootstrap_replicates,
        bootstrap_confidence=args.bootstrap_confidence,
        bootstrap_seed=args.bootstrap_seed,
    )
    if args.summary_only:
        payload.pop("test_sample_ids", None)
        payload.pop("test_group_ids", None)
        for model in payload["models"].values():
            model.pop("test_probabilities", None)
    _json_dump(payload)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "verify": _run_verify,
        "fixed": _run_fixed,
        "analyze": _run_analyze,
        "weights": _run_weights,
        "logits": _run_logits,
        "benchmark": _run_benchmark,
    }
    try:
        return handlers[args.command](args)
    except (
        ComputationLimitError,
        FileNotFoundError,
        ImportError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as error:
        if getattr(args, "json", False):
            _json_dump(
                {
                    "passed": False,
                    "error": type(error).__name__,
                    "message": str(error),
                }
            )
        else:
            print(f"error: {error}", file=sys.stderr)
        return 2


def entrypoint() -> None:
    raise SystemExit(main())


__all__ = ["build_parser", "entrypoint", "main"]
