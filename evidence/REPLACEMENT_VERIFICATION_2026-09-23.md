# Repository Replacement Verification — 2026-09-23

## Stage 1

- `tests/test_stage1_coordination.py`: **24 passed**.
- HMT cards HM-S01-01 through HM-S01-14 were executed as constituent runs and each returned PASS after the Round-2 corrections.
- HM-S01-05 now includes deliberate ledger-admission failure with zero causal drift/evidence drift.
- HM-S01-06 includes the same failure class as a ledger-completeness/orphan check.
- HM-S01-10 includes historical transaction-ID reuse, repeated persisted epoch, and skipped/future persisted epoch attacks.
- HM-S01-11 crash/replay passed all eight declared crash points in isolated execution.

The all-in-one HMT process exceeded the execution budget of the current tool host after the heavy load card. That host timeout is not counted as a PASS and is not treated as a model failure; the constituent card results above are the evidence available from this replacement pass.

## Stage 2 draft

`drafts/stage2/tests/test_stage2_matter.py`: **25 passed**.

This does not promote Stage 2. The candidate remains quarantined because the supplied governance/review chain does not establish the Stage-1 independent freeze verdict claimed inside the candidate's original contract.
