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

---

## Addendum — post-replacement corrections, 2026-09-23

The original record above is unchanged. This addendum covers three commits made after the replacement, in one session that both reviewed and corrected the code. **It is dependent (builder-side) evidence only. It is not an independent review and does not establish any freeze verdict.**

### Commits

| Commit | Change |
|---|---|
| `1714654` | Four ledger/checkpoint integrity defects (below, C1–C4). |
| `f3275db` | `causal_state_digest` made atomic across authorities (C5). |
| `03b8eff` | Malformed proposals rejected individually (C6); arbitration trust assumption documented (no behaviour change). |

### Defects found and corrected

Each defect was reproduced against the unmodified code before its fix. Each has a permanent regression test that fails on the pre-fix source and passes on the corrected source.

| ID | Defect (pre-fix behaviour) | Correction |
|---|---|---|
| C1 | A provenance-rejected proposal left no ledger record; its `transaction_id` then committed in a later epoch, contradicting run-global transaction-ID uniqueness. | Every proposal in an admitted batch leaves ledger evidence; REJECTED entries are exempt from provenance admissibility, COMMITTED entries are not. |
| C2 | `load_checkpoint` accepted authority state edited after writing (value 5 → 999999) while the ledger still verified; live state diverged from replay. | Checkpoint authority state/versions must equal `ledger.replay_state()` or loading raises `ProvenanceError`. |
| C3 | Imported records carrying a foreign `config_fingerprint` (digests recomputed) passed `verify_chain`. | `verify_chain` rejects any record whose fingerprint differs from the ledger's. |
| C4 | An exception other than `AuthorityError`/`ValueError` during domain execution left other winners prepared/staged; `checkpoint()` then failed permanently ("clean transaction boundary"). | `resolve` aborts every winner on any exception, then re-raises. Covered for serial and thread-pool paths. |
| C5 | `causal_state_digest` read authorities through separate projections; a cross-authority commit between them produced a digest of a combined state that never existed. | All resource locks held in canonical order for the whole read, as in `checkpoint()`. |
| C6 | One proposal with a proposer-attributable shape defect (empty mutations, duplicate resource, unknown authority, unknown resource) raised and blocked every proposal in the epoch. | That proposal alone is REJECTED and recorded (ID burned); others proceed. Batch-integrity errors still fail the whole call with zero state/evidence change. |

### Changed existing assertions

Two pre-existing tests encoded the corrected behaviour and were updated. Neither weakens its safety check (state unchanged is still asserted):

- `test_malformed_authoritative_provenance_rejected_before_state_change`: `ledger.records == ()` → exactly one REJECTED record with no committed mutations (C1).
- `test_s1_11_unknown_authority_cannot_be_mutated`: `pytest.raises(ValueError)` → REJECTED result with an "unknown authority" reason (C6).

No HMT gate file (`qualification/hmt_stage1_gate.py`) or locked manifest was modified.

### Verification at `03b8eff`

Environment: CPython 3.11.15, Linux x86_64, 4 CPUs.

| Check | Result | Status |
|---|---|---|
| HMT Stage-1 Gate, monolithic `qualification/hmt_stage1_gate.py` | **14/14 PASS**, exit 0 (HM-S01-07 ≈ 34 s; total ≈ 36 s) | DIRECTLY VERIFIED |
| `tests/test_stage1_coordination.py` | **36 passed, 0 failed** (24 original + 12 new) | VERIFIED WITH CAVEAT — see below |
| `drafts/stage2/tests/test_stage2_matter.py` | **25 passed** (Stage-2 source unchanged) | VERIFIED WITH CAVEAT — see below |
| `qualification/benchmark_stage1.py` | exit 0 | DIRECTLY VERIFIED |
| `qualification/reproduce_stage1.py` | exit 1 | NOT TESTABLE on this host — see below |

The monolithic gate completed on this host. This supersedes, for this host only, the earlier note that the all-in-one runner exceeded the execution budget.

**Caveat — pytest not used.** pytest could not be installed on this host. The pytest suites were run by a minimal stand-in, not committed, that implements only `raises(match=)`, `mark.parametrize`, `tmp_path` and `monkeypatch` and calls the unmodified test functions. The stand-in's detection was confirmed: new tests failed on pre-fix source. A real `pytest` run remains outstanding.

**`reproduce_stage1.py` not testable here.** It stops at its first step (no pytest), and it requires `UPSTREAM/AGE_OF_AGENTUS_MASTER_GATE9_REVIEW_CANDIDATE_2026-09-04_RESUBMISSION.zip`, which is not in the repository. It cannot pass on a fresh clone until that archive is supplied or the step is made optional.

### Recorded, not corrected

- **Arbitration gaming (trust assumption).** Proposal/transaction IDs are proposer-chosen and the run seed is readable, so a deliberately hostile kernel could search for conflict-winning IDs. Stage 1 treats kernels as non-hostile. The assumption is recorded in `HRM_STAGE1_ARCHITECTURE_v0.2.md` §Deterministic arbitration. The versioned contract was not edited.
- **Consumers of causal edges.** REJECTED records may carry inadmissible causal parents (that is why they were rejected). Causal-graph analysis must use COMMITTED records only; `replay_state` already does.
