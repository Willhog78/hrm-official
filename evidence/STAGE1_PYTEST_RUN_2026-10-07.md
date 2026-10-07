# Stage-1 real pytest run — 2026-10-07

**Purpose.** STATUS.md listed "no real pytest run has happened" as one of the reasons Stage 1 is not frozen. Earlier Stage-1 results came from a minimal pytest stand-in, because pytest was unavailable on that host, and CI never ran (see "CI" below). This record closes that one item.

**What this does not do.** It does not freeze Stage 1. The other freeze blockers are unchanged:
- S1.12 is unevidenced until the `UPSTREAM/` Agentus archive is supplied;
- non-atomic checkpoint writes are untested;
- unbounded publish bookkeeping is untested;
- undetectable genesis tampering with an empty ledger is untested.

## Environment

| | |
|---|---|
| Commit | `4fd0224f2594fac1cd1aa3a2568ae50a934d0de9` (`main`, after PR #33) |
| Host | Claude Code cloud container, Linux 6.18.44 |
| Python | 3.13.16 (CI pins 3.11; no 3.11 run has happened) |
| pytest | 9.1.1, installed with `pip install pytest` for this run |

## Commands and results

The exact command from README.md "Reproduce":

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -o addopts='' -q tests/test_stage1_coordination.py
```

Result: **43 passed in 0.82 s.**

The HMT contract cards, same flags:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -o addopts='' -q tests/test_stage1_hmt_contract.py
```

Result: **14 passed in 37.04 s.**

No failures, errors or skips.

## CI

CI has never produced a test result for this repository. All 119 runs of the `Stage-1 verification` workflow (runs 1–119, 2026-09-23 to 2026-10-07) failed before any step ran. GitHub's annotation on the jobs, checked for runs 1, 11 and 119, says:

> The job was not started because your account is locked due to a billing issue.

See STATUS.md, "Verification infrastructure".
