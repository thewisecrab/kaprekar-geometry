#!/usr/bin/env python3
"""Regenerate the repository's exact verification and dynamics artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
LOCAL_SRC = (ROOT / "src").resolve()
sys.path.insert(0, str(LOCAL_SRC))
kaprekar = import_module("kaprekar")
sys.path.insert(0, str(ROOT))
independent_oracle = import_module("proofs.independent_oracle")

PACKAGE_FILE = Path(kaprekar.__file__).resolve()
if LOCAL_SRC not in PACKAGE_FILE.parents:
    raise RuntimeError(
        f"reproduction must use the workspace package, loaded {PACKAGE_FILE}"
    )


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _source_files() -> tuple[Path, ...]:
    explicit = (
        ROOT / ".gitignore",
        ROOT / "CITATION.cff",
        ROOT / "README.md",
        ROOT / "output" / "arxiv" / "kaprekar_geometry_arxiv_source.tar.gz",
        ROOT / "output" / "pdf" / "kaprekar_geometry_arxiv.pdf",
        ROOT / "pyproject.toml",
        ROOT / "kaprekar_logit_geometry_paper.pdf",
        ROOT / "kaprekar_verification.py",
    )
    discovered = tuple(
        path
        for directory, pattern in (
            (".github", "*.yml"),
            ("docs", "*.md"),
            ("paper", "*.md"),
            ("paper", "*.tex"),
            ("paper", "*.bib"),
            ("proofs", "*.md"),
            ("proofs", "*.py"),
            ("proofs", "*.lean"),
            ("proofs", "*.json"),
            ("proofs", "*.toml"),
            ("proofs", "lean-toolchain"),
            ("scripts", "*.py"),
            ("src/kaprekar", "*.py"),
            ("tests", "*.py"),
        )
        for path in (ROOT / directory).rglob(pattern)
        if path.is_file()
        and ".lake" not in path.parts
        and "__pycache__" not in path.parts
    )
    return tuple(sorted(set(explicit + discovered)))


def _named_source_files() -> dict[str, Path]:
    return {
        "original_pdf": ROOT / "kaprekar_logit_geometry_paper.pdf",
        "authored_arxiv_pdf": (
            ROOT / "output" / "pdf" / "kaprekar_geometry_arxiv.pdf"
        ),
        "arxiv_main_tex": ROOT / "paper" / "arxiv" / "main.tex",
        "arxiv_references": ROOT / "paper" / "arxiv" / "references.bib",
        "arxiv_source_bundle": (
            ROOT
            / "output"
            / "arxiv"
            / "kaprekar_geometry_arxiv_source.tar.gz"
        ),
        "compatibility_verifier": ROOT / "kaprekar_verification.py",
        "theory_addendum": ROOT / "paper" / "theory_addendum.md",
        "proof_companion": ROOT / "paper" / "proof_companion.md",
        "independent_oracle": ROOT / "proofs" / "independent_oracle.py",
        "lean_proofs": ROOT / "proofs" / "lean" / "KaprekarProofs.lean",
    }


def _tree_sha256(paths: tuple[Path, ...]) -> str:
    digest = sha256()
    for path in paths:
        relative = path.relative_to(ROOT).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _check_manifest() -> int:
    manifest_path = ROOT / "results" / "manifest.json"
    if not manifest_path.is_file():
        print(f"missing manifest: {manifest_path}", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_files = _source_files()
    expected_paths = [path.relative_to(ROOT).as_posix() for path in source_files]
    errors: list[str] = []

    if manifest.get("source_tree_files") != expected_paths:
        errors.append("source_tree_files does not match the current release tree")
    if manifest.get("source_tree_sha256") != _tree_sha256(source_files):
        errors.append("source_tree_sha256 is stale")

    recorded_sources = manifest.get("source_sha256", {})
    for name, path in _named_source_files().items():
        if recorded_sources.get(name) != _sha256(path):
            errors.append(f"source_sha256.{name} is stale")

    recorded_artifacts = manifest.get("artifact_sha256", {})
    for name in manifest.get("artifacts", []):
        path = ROOT / "results" / name
        if not path.is_file() or recorded_artifacts.get(name) != _sha256(path):
            errors.append(f"artifact_sha256.{name} is stale or missing")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("Run python3 scripts/reproduce.py to refresh evidence.", file=sys.stderr)
        return 1

    print("Manifest source tree and artifact hashes are current.")
    return 0


def _regenerate() -> int:
    output = ROOT / "results"
    output.mkdir(exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    source_files = _source_files()

    verification = kaprekar.verify_ranges()
    verification_payload = verification.to_dict()
    verification_payload.update(
        {
            "generated_at": generated_at,
            "claim_scope": (
                "exhaustive factorization and image equality for the 49-case "
                "base 2..8, width 1..7 grid"
            ),
            "decimal_fixed_spectra": {
                str(width): [
                    {"spectrum": list(spectrum), "value": value}
                    for spectrum, value in kaprekar.fixed_spectra(10, width)
                ]
                for width in range(3, 9)
            },
        }
    )
    _write_json(output / "paper_verification.json", verification_payload)

    systems: dict[str, object] = {}
    for width in range(3, 9):
        analysis = kaprekar.analyze_functional_graph(10, width)
        payload = analysis.to_dict(include_states=False)
        payload["uniform_entropy_trajectory"] = [
            point.to_dict()
            for point in kaprekar.uniform_entropy_trajectory(analysis)
        ]
        for attractor in payload["attractors"]:
            attractor["raw_basin_probability"] = (
                attractor["raw_basin_size"] / analysis.raw_state_count
            )
        systems[str(width)] = payload
    _write_json(
        output / "decimal_dynamics.json",
        {
            "generated_at": generated_at,
            "domain": "all fixed-width decimal strings including leading zeros",
            "systems": systems,
        },
    )

    proof_certificate = independent_oracle.build_certificate(
        base_min=2,
        base_max=8,
        digits_min=1,
        digits_max=7,
    )
    independent_oracle.verify_certificate_envelope(proof_certificate)
    _write_json(output / "independent_proof_certificate.json", proof_certificate)

    artifact_names = (
        "paper_verification.json",
        "decimal_dynamics.json",
        "independent_proof_certificate.json",
    )
    _write_json(
        output / "manifest.json",
        {
            "generated_at": generated_at,
            "python": platform.python_version(),
            "package_version": kaprekar.__version__,
            "source_tree_sha256": _tree_sha256(source_files),
            "source_tree_files": [
                path.relative_to(ROOT).as_posix() for path in source_files
            ],
            "source_sha256": {
                name: _sha256(path) for name, path in _named_source_files().items()
            },
            "artifact_sha256": {
                name: _sha256(output / name) for name in artifact_names
            },
            "artifacts": list(artifact_names),
            "nondeterministic_fields": [
                "generated_at",
                "duration_seconds",
            ],
        },
    )
    print(f"Wrote exact artifacts to {output}")
    return 0


def main() -> int:
    if sys.argv[1:] == ["--check"]:
        return _check_manifest()
    if sys.argv[1:]:
        print("usage: reproduce.py [--check]", file=sys.stderr)
        return 2
    return _regenerate()


if __name__ == "__main__":
    raise SystemExit(main())
