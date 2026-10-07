"""One entry point for the four test tiers.

  python -m qualification.genesis.tiers micro [topic ...]     # seconds
  python -m qualification.genesis.tiers smoke [--days 90]     # ~1 min
  python -m qualification.genesis.tiers diagnostic <set>      # minutes
  python -m qualification.genesis.tiers full                  # hours; 20 seeds x 730 days
  python -m qualification.genesis.tiers fast                  # micro + smoke (development loop)

Topics: thirst, food, hunting, stone, fibers, learning, infant_care, cannibalism.
Diagnostic sets: see qualification/genesis/diagnostic.py.
See docs/architecture/TESTING_TIERS.md.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MICRO_DIR = ROOT / "tests" / "genesis" / "micro"


def micro(topics: list[str]) -> int:
    files = [str(MICRO_DIR / f"test_micro_{t}.py") for t in topics] if topics else [str(MICRO_DIR)]
    missing = [f for f in files if not Path(f).exists()]
    if missing:
        known = sorted(p.stem.removeprefix("test_micro_") for p in MICRO_DIR.glob("test_micro_*.py"))
        print(f"unknown micro topic(s): {missing}; known: {known}")
        return 2
    t = time.perf_counter()
    # -s shows the cannibalism diagnostic printout; -rx lists known defects.
    status = subprocess.call([sys.executable, "-m", "pytest", "-q", "-s", "-rx", *files], cwd=ROOT)
    print(f"micro wall time {time.perf_counter() - t:.1f}s  RESULT: {'PASS' if status == 0 else 'FAIL'}", flush=True)
    return status


def full(extra: list[str]) -> int:
    """The existing long validation; unchanged, just launched from here."""
    env = dict(os.environ)
    env.setdefault("HRM_SEEDS", "all")
    env.setdefault("HRM_DAYS", "730")
    return subprocess.call(["sh", str(ROOT / "experiments" / "genesis" / "run_g10_3_railway.sh"), *extra], cwd=ROOT, env=env)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print(__doc__)
        return 0
    tier, rest = argv[0], argv[1:]
    if tier == "micro":
        return micro(rest)
    if tier == "smoke":
        from qualification.genesis.smoke import main as smoke
        return smoke(rest)
    if tier == "diagnostic":
        from qualification.genesis.diagnostic import main as diagnostic
        return diagnostic(rest)
    if tier == "full":
        return full(rest)
    if tier == "fast":
        from qualification.genesis.smoke import main as smoke
        t = time.perf_counter()
        m = micro([])
        s = smoke(rest)
        print(f"\nFAST DEVELOPMENT: micro {'PASS' if m == 0 else 'FAIL'}, smoke {'PASS' if s == 0 else 'FAIL'}, "
              f"wall time {time.perf_counter() - t:.0f}s", flush=True)
        return m or s
    print(f"unknown tier {tier!r}\n{__doc__}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
