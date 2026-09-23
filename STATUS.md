# HRM Current Status

**Repository baseline:** clean rebuild; old June HRM kernel removed from the working tree.

## Stage 0

**FROZEN / CLOSED.** The salvage record treats old HRM as contaminated archaeology: ideas, equations, tests, and empirical questions may be inspected, but implementation does not carry forward by default.

## Stage 1

**ACTIVE — corrected post-Round-2, post-replacement and post-self-review; not frozen.**

The supplied dependent Round-2 review found three blocking defects: historical transaction-ID ambiguity, caller-trusted epoch admission, and ledger admission occurring after causal materialization. The active source in this repository corrects those three defects and adds permanent hostile regressions.

Local verification performed during the repository replacement:

- Stage-1 coordination regression suite: **24/24 PASS**.
- HMT Stage-1 cards: **14/14 PASS when executed as isolated/constituent card runs**.
- The monolithic HMT runner exceeded this tool host's execution budget after the load card; that host limitation is recorded rather than counted as evidence.

### Post-replacement corrections (2026-09-23)

A later dependent session found and corrected six further defects (C1–C6). Full record: `evidence/REPLACEMENT_VERIFICATION_2026-09-23.md`, addendum.

- **C1:** provenance-rejected transaction IDs were reusable.
- **C2:** checkpoints with edited state loaded silently.
- **C3:** foreign-config ledger records were accepted on import.
- **C4:** unexpected errors leaked staged transactions and blocked checkpoints.
- **C5:** the causal-state digest was not atomic across authorities.
- **C6:** one malformed proposal failed the whole epoch; it now rejects only itself.

The arbitration trust assumption (non-hostile kernels) is recorded in `stage1/HRM_STAGE1_ARCHITECTURE_v0.2.md`.

### Self-review (2026-09-23)

Under Governance Amendment v2, independent review is replaced by self-review. The first self-review (`reviews/HRM_STAGE1_SELF_REVIEW_2026-09-23.md`) found three RED defects and three lesser issues; all RED items are corrected:

- **F1 (RED):** IDs containing `:` could give two records the same record ID, corrupting the ledger. Record IDs are now collision-free and checked.
- **F2 (RED):** a rejected transaction could be cited as a cause. Only committed records are legal causal parents, at admission and on import.
- **F3 (RED):** the C5 regression test did not protect C5. Rewritten; now fails when the fix is removed.
- **F4:** `feedback_lag_ticks` values other than 1 were accepted but not enforced. They are now rejected; the lag is fixed at 1 tick in Stage 1.
- **F5:** `reproduce_stage1.py` exited 0 on a partial run; it now exits 2.

Current verification:

- Stage-1 coordination regression suite: **43/43 PASS**, run via a minimal pytest stand-in because pytest was unavailable on that host. Every correction's test was shown to fail with that correction removed. **A real pytest run is still outstanding** (CI cannot obtain a runner; see the Actions job page for the account/repository setting that blocks it).
- HMT Stage-1 Gate: **14/14 PASS as one monolithic run** (≈36 s).
- `qualification/reproduce_stage1.py`: without the `UPSTREAM/` Agentus archive (not in the repository) it skips the Agentus step, prints `STAGE1_REPRODUCTION_PARTIAL (S1.12 not evidenced)` and exits 2. `--require-upstream` fails immediately if the archive is absent.

**Why Stage 1 is still not frozen:**

- S1.12 is unevidenced until the archive is supplied;
- no real pytest run has happened;
- three reported risks are untested: non-atomic checkpoint writes, unbounded publish bookkeeping, and undetectable genesis tampering with an empty ledger.

## Stage 2

**DRAFT / QUARANTINED.** The supplied Matter Slice-A candidate passes **25/25** of its own tests, but its contract contains a Stage-1-freeze assertion that is not established by the supplied review chain. It is retained under `drafts/stage2/` without promotion to the active baseline.
