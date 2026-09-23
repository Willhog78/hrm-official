# HRM Current Status

**Repository baseline:** clean rebuild; old June HRM kernel removed from the working tree.

## Stage 0

**FROZEN / CLOSED.** The salvage record treats old HRM as contaminated archaeology: ideas, equations, tests, and empirical questions may be inspected, but implementation does not carry forward by default.

## Stage 1

**ACTIVE — corrected post-Round-2 and post-replacement; not declared frozen here.**

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

Current verification at `03b8eff`:

- Stage-1 coordination regression suite: **36/36 PASS** (24 original + 12 new). Run via a minimal pytest stand-in because pytest was unavailable on that host. **A real pytest run is still outstanding.**
- HMT Stage-1 Gate: **14/14 PASS as one monolithic run** (≈36 s).
- `qualification/reproduce_stage1.py` now runs on a fresh clone when pytest is installed. Without the `UPSTREAM/` Agentus archive (not in the repository) it skips the Agentus step and prints `STAGE1_REPRODUCTION_PARTIAL (S1.12 not evidenced)` instead of a pass; `--require-upstream` fails immediately if the archive is absent. **S1.12 remains unevidenced until the archive is supplied.**

These corrections were made by the same session that reviewed the code. They are dependent evidence only. The required independent review must cover them.

The supplied review chain does not contain the final independent architecture verdict required to call Stage 1 frozen. Therefore this repository does not claim that verdict.

## Stage 2

**DRAFT / QUARANTINED.** The supplied Matter Slice-A candidate passes **25/25** of its own tests, but its contract contains a Stage-1-freeze assertion that is not established by the supplied review chain. It is retained under `drafts/stage2/` without promotion to the active baseline.
