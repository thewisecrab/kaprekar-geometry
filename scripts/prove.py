#!/usr/bin/env python3
"""Generate or independently recompute a deterministic proof certificate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from proofs.independent_oracle import (  # noqa: E402
    build_certificate,
    recompute_and_verify_certificate,
    verify_certificate_envelope,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", type=Path, help="write a new certificate")
    action.add_argument("--verify", type=Path, help="recompute and verify a certificate")
    action.add_argument(
        "--verify-envelope",
        type=Path,
        help="verify only the artifact digest and internal totals",
    )
    parser.add_argument("--base-min", type=int, default=2)
    parser.add_argument("--base-max", type=int, default=8)
    parser.add_argument("--digits-min", type=int, default=1)
    parser.add_argument("--digits-max", type=int, default=7)
    return parser


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = _parser().parse_args()
    if args.write is not None:
        certificate = build_certificate(
            base_min=args.base_min,
            base_max=args.base_max,
            digits_min=args.digits_min,
            digits_max=args.digits_max,
        )
        path = args.write if args.write.is_absolute() else ROOT / args.write
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(certificate, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"proved {certificate['scope']['case_count']} cases and "
            f"{certificate['scope']['raw_states_checked']:,} raw states; "
            f"wrote {path}"
        )
        print(f"certificate_sha256={certificate['certificate_sha256']}")
        return 0

    path = args.verify if args.verify is not None else args.verify_envelope
    assert path is not None
    path = path if path.is_absolute() else ROOT / path
    payload = _load(path)
    if not isinstance(payload, dict):
        raise ValueError("certificate root must be a JSON object")
    if args.verify is not None:
        recompute_and_verify_certificate(payload)
        mode = "fully recomputed"
    else:
        verify_certificate_envelope(payload)
        mode = "envelope"
    print(f"{mode} proof certificate is valid: {path}")
    print(f"certificate_sha256={payload['certificate_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
