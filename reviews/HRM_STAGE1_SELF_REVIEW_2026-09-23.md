# HRM Stage 1 — Self-Review, 2026-09-23

**Basis:** Governance Amendment v2 (self-review).
**Candidate:** `main` at `9869bed` (Stage-1 rebuild plus corrections C1–C6).
**Reviewer:** the same Claude session that made corrections C1–C6, so this review is not independent (see Amendment v2).
**Discipline:** findings were frozen before any fix. The builder response is a separate section below.

## Baseline at `9869bed`

| Check | Result | Status |
|---|---|---|
| HMT Stage-1 Gate, monolithic | 14/14 PASS | DIRECTLY VERIFIED |
| `tests/test_stage1_coordination.py` | 36/36 | VERIFIED WITH CAVEAT (pytest stand-in; pytest unavailable on host) |

## Findings (frozen)

| # | Grade | Finding | Evidence |
|---|---|---|---|
| F1 | **RED** | Record IDs were `E{epoch}:{tx}:{pid}` and IDs may contain `:`. `("a:b","c")` and `("a","b:c")` produced the same record ID. `prepare_batch` checked record IDs only against history, not within the batch. Both proposals committed; `verify_chain()` then returned `False` and export/import failed, so any later checkpoint could not be reloaded. Pre-existing; missed by the earlier dependent review. | DIRECTLY VERIFIED: both COMMITTED, both `E000000000000:a:b:c`, `verify_chain` False, import raised `invalid imported ledger chain`. |
| F2 | **RED** | A REJECTED transaction was accepted as a causal parent, because admission checked parents against all recorded IDs. A committed record could claim a cause that never happened (S1.7, S1.13). Pre-existing; widened by C1, which records more rejected IDs. | DIRECTLY VERIFIED: stale `NEVER-HAPPENED` REJECTED; child citing it COMMITTED with that parent. |
| F3 | **RED** | The C5 regression test did not protect C5. It hooked `_keys_for_projection`, which the fixed digest never calls. With the digest's locking removed, the test still passed. Reviewer's own work. | VERIFIED by mutation (suite ran: 36 passed with the fix removed). |
| F4 | Major | `ScheduleSpec.feedback_lag_ticks` was accepted and passed to callbacks but never enforced. With lag 5 declared, a producer read the previous epoch's results and cited them as parents. Only a lag of 1 is enforced (by the ledger). | DIRECTLY VERIFIED: lag 5 declared; values read at epochs 0/1/2 were 0/1/2; all COMMITTED. |
| F5 | Minor | `reproduce_stage1.py` exited 0 on a PARTIAL result, so exit-code-only automation reads it as a pass. Reviewer's own work. | VERIFIED by code reading. |
| F6 | Minor | `STATUS.md` labelled verification "at `03b8eff`" while `main` was `9869bed` (later commits: CI, reproduce script, docs only). | VERIFIED |

**Reported, not tested:** `write_checkpoint` is not atomic (a crash mid-write leaves a corrupt file; no crash card covers it). `TransactionFabric._published` grows without bound. Genesis tampering is undetectable while the ledger has zero epoch blocks.

**Not testable here:** S1.12 (needs the `UPSTREAM/` Agentus archive). A real pytest run (CI cannot obtain a runner; see `STATUS.md`).

**Verdict at `9869bed`:** not freeze-ready (three RED).

## Builder response

| # | Correction | Regression test |
|---|---|---|
| F1 | Record ID is `E{epoch:012d}:` + canonical JSON of `[transaction_id, proposal_id]` (injective). `prepare_batch` also rejects duplicate record IDs within a batch. `verify_chain` rejects any record whose ID is not derived from its own fields. | `test_ids_containing_separators_cannot_collide_or_corrupt_the_ledger`, `test_imported_record_with_non_derived_record_id_is_rejected` |
| F2 | Only COMMITTED records' IDs are legal causal parents at admission. `verify_chain` enforces the same on import: a committed record may cite only committed records from earlier epochs. | `test_rejected_transaction_cannot_be_a_causal_parent`, `test_imported_committed_record_citing_rejected_parent_is_rejected` |
| F3 | Test rewritten: a port wrapper starts a cross-authority commit after A is read and waits for it before B is read. An atomic digest blocks the writer; a non-atomic one lets it commit in between. | `test_causal_state_digest_is_atomic_across_authorities` |
| F4 | Decision (project owner, on recommendation): keep the lag fixed at 1 tick. `ScheduleSpec` rejects any other value at registration, with the reason. `test_s1_2` declared lag 2 without relying on it; changed to 1 (its assertions are about cadence only). | `test_feedback_lag_other_than_one_is_rejected` (lags 0, 2, 5) |
| F5 | PARTIAL now exits with code 2. | Checked with the command runner stubbed: exit code 2. |
| F6 | `STATUS.md` updated. | — |

The three reported-not-tested items are not corrected; they remain open.

### Verification of the response

| Check | Result | Status |
|---|---|---|
| New tests on pre-fix `9869bed` source | All new tests fail | VERIFIED |
| Mutation check: each correction removed in turn (F1 derived-ID check, F2 admission rule, F2 import rule, F3/C5 digest locking, F4 lag check), plus C1–C4 and C6 re-checked | Every mutant fails at least one test | VERIFIED (harness requires the suite to have run; a crashed suite counts as invalid, not as survival) |
| `tests/test_stage1_coordination.py` | 43/43 | VERIFIED WITH CAVEAT (pytest stand-in) |
| HMT Stage-1 Gate, monolithic | 14/14 PASS | DIRECTLY VERIFIED |
| `benchmark_stage1.py` | exit 0 | DIRECTLY VERIFIED |
| `drafts/stage2` suite | 25/25 (source unchanged) | VERIFIED WITH CAVEAT (pytest stand-in) |

**Reviewer's own error during the response:** the first mutation harness reported one mutant as surviving when the mutated module failed to import (the suite never ran). The harness was fixed to require a completed run. The F3 finding was re-checked under the fixed harness and holds.

**Note on the pre-fix run:** `test_s1_14_checkpoint_restart_fresh_process_determinism` also failed against the pre-fix source. That test starts a child process on the repository's current source, so mixing pre-fix parent code with post-fix child code changes record IDs. It passes on the corrected source. This is a harness artefact, not a defect.

## Verdict after response

All RED findings are corrected and verified. Stage 1 is **still not freeze-ready** against its own exit criteria:

- S1.12 is not evidenced (the `UPSTREAM/` archive is missing);
- no real pytest run has happened;
- three reported risks remain untested.
