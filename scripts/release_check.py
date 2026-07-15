#!/usr/bin/env python3
"""Run the mandatory extra-enabled, exhaustive release test gate."""

from __future__ import annotations

from importlib.util import find_spec
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if find_spec("numpy") is None:
        print(
            "release check requires NumPy; install the benchmark extra first",
            file=sys.stderr,
        )
        return 2

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src"))
    os.environ["KAPREKAR_RUN_SLOW_TESTS"] = "1"
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
