#!/usr/bin/env python3
"""Run a reproducibly pinned external kernel check of the Lean development.

The lean-action v1.5.0 nanoda integration currently combines an NDJSON
lean4export build with a legacy plaintext nanoda parser.  This script pins a
compatible exporter and checker independently, exports the complete
``KaprekarProofs`` environment, and rejects any declaration that depends on an
axiom outside the small explicit allowlist below (including ``sorryAx``).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
LEAN_PROJECT = ROOT / "proofs" / "lean"

LEAN4EXPORT_REPOSITORY = "https://github.com/leanprover/lean4export.git"
LEAN4EXPORT_REVISION = "4e7915201d3f9f04470d9eae002fa695f7cdc589"
NANODA_REPOSITORY = "https://github.com/ammkrn/nanoda_lib.git"
NANODA_REVISION = "f58f2f6d535e189a40fcb02ede8eb95f97a92d37"

PERMITTED_AXIOMS = (
    "propext",
    "Classical.choice",
    "Quot.sound",
    "Lean.trustCompiler",
)


def _run(
    command: list[str],
    *,
    cwd: Path,
    stdout: object | None = None,
) -> None:
    print(f"+ {shlex.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True, stdout=stdout)


def _output(command: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def _checkout(repository: str, revision: str, destination: Path) -> None:
    destination.mkdir(parents=True)
    _run(["git", "init", "--quiet"], cwd=destination)
    _run(["git", "remote", "add", "origin", repository], cwd=destination)
    _run(
        ["git", "fetch", "--quiet", "--depth", "1", "origin", revision],
        cwd=destination,
    )
    _run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], cwd=destination)
    actual = _output(["git", "rev-parse", "HEAD"], cwd=destination)
    if actual != revision:
        raise RuntimeError(f"expected {revision}, checked out {actual}")


def _require_tools() -> None:
    missing = [name for name in ("cargo", "git", "lake") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(f"missing required tools: {', '.join(missing)}")


def _check(module: str, workspace: Path) -> None:
    exporter_source = workspace / "lean4export"
    checker_source = workspace / "nanoda"
    export_path = workspace / "KaprekarProofs.ndjson"
    config_path = workspace / "nanoda-config.json"

    _checkout(LEAN4EXPORT_REPOSITORY, LEAN4EXPORT_REVISION, exporter_source)
    shutil.copy2(LEAN_PROJECT / "lean-toolchain", exporter_source / "lean-toolchain")
    _run(["lake", "build"], cwd=exporter_source)

    _checkout(NANODA_REPOSITORY, NANODA_REVISION, checker_source)
    _run(["cargo", "build", "--release", "--locked"], cwd=checker_source)

    exporter = exporter_source / ".lake" / "build" / "bin" / "lean4export"
    with export_path.open("wb") as export_file:
        _run(
            ["lake", "env", str(exporter), module],
            cwd=LEAN_PROJECT,
            stdout=export_file,
        )

    config = {
        "export_file_path": str(export_path),
        "use_stdin": False,
        "permitted_axioms": list(PERMITTED_AXIOMS),
        # Unused declarations such as sorryAx are skipped. Any declaration
        # that actually depends on one then fails because it is absent.
        "unpermitted_axiom_hard_error": False,
        "num_threads": max(1, int(os.environ.get("KAPREKAR_NANODA_THREADS", "1"))),
        "nat_extension": True,
        "string_extension": True,
        # The skipped-axiom list is still included in nanoda's success line.
        # This flag only asks its pretty-printer to emit every admitted axiom,
        # which requires a separate output destination and is not a proof check.
        "print_axioms": False,
        "print_success_message": True,
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    checker = checker_source / "target" / "release" / "nanoda_bin"
    _run([str(checker), str(config_path)], cwd=workspace)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export and independently kernel-check the Lean proof environment."
    )
    parser.add_argument("--module", default="KaprekarProofs")
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Retain build and export files in this directory for debugging.",
    )
    args = parser.parse_args()

    _require_tools()
    if args.work_dir is not None:
        workspace = args.work_dir.resolve()
        if workspace.exists() and any(workspace.iterdir()):
            raise RuntimeError(f"work directory must be empty: {workspace}")
        workspace.mkdir(parents=True, exist_ok=True)
        _check(args.module, workspace)
    else:
        with tempfile.TemporaryDirectory(prefix="kaprekar-nanoda-") as temporary:
            _check(args.module, Path(temporary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
