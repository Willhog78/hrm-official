from __future__ import annotations

import argparse
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "UPSTREAM" / "AGE_OF_AGENTUS_MASTER_GATE9_REVIEW_CANDIDATE_2026-09-04_RESUBMISSION.zip"
PREFIX = "AGE_OF_AGENTUS_MASTER_GATE9_REVIEW_CANDIDATE_2026-09-04_RESUBMISSION/CURRENT_IMPLEMENTATION/GATE2_MATTER/"


def run(cmd, *, cwd, env):
    print("$", " ".join(map(str, cmd)), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, env=env)
    if proc.returncode:
        raise SystemExit(proc.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-benchmark", action="store_true")
    ap.add_argument(
        "--require-upstream",
        action="store_true",
        help="fail if the UPSTREAM Agentus archive is absent (use for scored/reviewer runs)",
    )
    args = ap.parse_args()
    if args.require_upstream and not UPSTREAM.is_file():
        raise SystemExit(f"missing required upstream archive: {UPSTREAM}")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}:{ROOT}"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTEST_ADDOPTS"] = ""

    # Fast Stage-1 regression suite.
    run([sys.executable, "-m", "pytest", "-q", "tests/test_stage1_coordination.py"], cwd=ROOT, env=env)

    # Locked HMT Stage-1 Gate. The standalone runner is the scored/reviewer lane;
    # it avoids dependence on whatever third-party pytest plugins happen to be
    # installed in the host environment.
    with tempfile.TemporaryDirectory(prefix="hrm_stage1_hmt_") as htd:
        hmt_out = Path(htd) / "hmt.json"
        run([sys.executable, "qualification/hmt_stage1_gate.py", "--output", str(hmt_out)], cwd=ROOT, env=env)

    if not args.skip_benchmark:
        run([sys.executable, "qualification/benchmark_stage1.py"], cwd=ROOT, env=env)

    if not UPSTREAM.is_file():
        # S1.12 (preserved Agentus tests) cannot be evidenced without the archive.
        # Never report a full reproduction pass when that step did not run.
        print(f"NOTICE: {UPSTREAM.relative_to(ROOT)} not found; Agentus S1.12 step SKIPPED", flush=True)
        print("STAGE1_REPRODUCTION_PARTIAL (S1.12 not evidenced)", flush=True)
        # Distinct non-zero code: automation must not read a partial run as a pass.
        raise SystemExit(2)

    with tempfile.TemporaryDirectory(prefix="hrm_stage1_agentus_") as td:
        out = Path(td)
        with zipfile.ZipFile(UPSTREAM) as z:
            for name in z.namelist():
                if name.startswith(PREFIX) and not name.endswith("/"):
                    rel = name[len(PREFIX):]
                    dest = out / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(z.read(name))
        uenv = os.environ.copy()
        uenv["PYTHONPATH"] = str(out / "src")
        uenv["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        uenv["PYTEST_ADDOPTS"] = ""
        run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=out, env=uenv)

    print("STAGE1_REPRODUCTION_PASS", flush=True)


if __name__ == "__main__":
    main()
