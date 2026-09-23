# Stage 1 Round-2 Correction Note v0.3

This note records the corrections applied to the active source after the dependent Round-2 review.

## DAR-S1-004 — Historical transaction identity

Transaction IDs are now run-global identifiers. Reuse of a previously committed transaction ID is rejected before authority preparation or causal mutation. Ledger verification and imported evidence also reject duplicate historical transaction IDs.

Permanent regression: `test_round2_dar_s1_004_transaction_ids_are_run_global`.

## DAR-S1-005 — Persisted epoch authority

The replay ledger now exposes the next admissible epoch. Genesis admits epoch 0; each finalized epoch advances the expected value by exactly one. Repeated/stale and skipped/future epochs are rejected before authority work. Explicit empty epochs remain legal evidence blocks.

Permanent regressions:

- `test_round2_dar_s1_005_epoch_admission_is_historical_not_caller_trusted`
- `test_sequential_epoch_contract_allows_explicit_empty_epochs`

## DAR-S1-006 — Ledger admission before materialization

Ledger processing is split into two phases:

1. `prepare_batch()` performs every rejection-capable provenance, identity, epoch, and digest operation without changing visible ledger state.
2. `commit_prepared_batch()` installs the already validated immutable batch without semantic revalidation.

Authority prepare/stage occurs before ledger admission but remains non-visible. If ledger preparation fails, staged authority work is aborted and no publication survives. Only after ledger preparation succeeds can causal state materialize. Affected resource locks remain held until the prevalidated evidence is finalized, preventing legal projections from observing new causal state without its corresponding ledger evidence.

Permanent regression: `test_round2_dar_s1_006_ledger_admission_failure_precedes_materialization`.

## Governance

These engineering corrections do not self-award the independent architecture PASS required for Stage-1 freeze.
