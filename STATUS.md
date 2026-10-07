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


## Genesis vertical slice

**ACTIVE.** The executable Genesis stack has advanced beyond the stale status text that previously ended at the quarantined Stage-2 draft.

Merged implementation and qualification assets now exist through:
- G0 integration;
- G1 physical world;
- G1.5 matter/elements;
- G2 producers;
- G3 consumers;
- G4 autonomous ecology;
- G5 human biology;
- G6 cognition;
- G7 general actions/learning;
- G8 multi-population;
- G9 read-only observer;
- G10.1 scaled substrate;
- G10.2 calibrated reference humans.

**Current active correction:** G10.2A survival affordances, adding terrain-conditioned rock/cave cover and condition-grown woody biomass before any long-run calibrated-human survival claim.

**G10.3 Agentus natural capacities (capacity model v1):** implemented behind `agentus_capacities_enabled` (default off; earlier fingerprints and ledgers unchanged). It adds:
- omnivorous ingestion (plant tissue, seeds, fresh animal tissue; wood and decayed tissue are not food);
- capture of live animals;
- movable stone with fracture and edges;
- fibers from plant, bark and tendon, with bindings that hold or fail;
- worn interlaced surfaces;
- learned food and interaction values;
- travel toward remembered food.

Specification, audit and limits: `docs/architecture/G10_3_AGENTUS_CAPACITIES.md`. Experimental evidence: `experiments/genesis/summaries/AGENTUS_CAPACITY_V1_2026-10-07.md`. Sustainable survival is not qualified.

**G10.4 survival bottlenecks: COMPLETE** (merged in PR #26; capacity model `capacity-v2`). Specification: `docs/architecture/G10_4_SURVIVAL_BOTTLENECKS.md`.
- Thirst is a baseline planning drive. It uses local or remembered water only and competes with hunger.
- Hunting requires approach and physical contact.
- Delayed credit flows through object history, and warmth counts as a reward.
- Repeated beneficial use is measured, and learning by observation applies to successes only.
- The animal population is diagnosed as limited by its life history (owner decision pending).

**G10.5 energy-budget realism: COMPLETE as an opt-in** (`agentus_physiology_version="reference-v2"`).
- It adds a fat reserve, lean catabolism, corrected nursing and Kleiber scaling.
- The default remains `reference-v1`. Whether v2 becomes the default is decided when long-run claims are made.

**Testing tiers: ACTIVE** (`docs/architecture/TESTING_TIERS.md`).
- The tiers are micro (about 2 s), smoke (about 25 s), diagnostic (about 2–4 min) and full (hours).
- The development loop is `python -m qualification.genesis.tiers fast`.
- The full 20-seed × 730-day batch is validation, not the default.
- **Advancement rule:** a mechanism advances when its physical and integrity contract holds. Long-horizon survival is reported, not used as a gate.

**G10.6 behavioural/locomotion integrity: IMPLEMENTED** (`docs/architecture/G10_6_BEHAVIORAL_INTEGRITY.md`; flag `agentus_behavior_integrity_enabled`, default on).
- Partial food is no longer abandoned.
- Dependents are carried, or walk one cell a day.
- Fatigue recovers with sleep.
- Blocked agent-days fell from 27% to 0% in the targeted diagnostic.

**Next: G10.7 communication and teaching** (see ROADMAP).

**Infrastructure ticket.** GitHub Actions `verify` fails before any step runs, on `main` as well as on PRs (runs 99–104). This is an Actions environment problem (billing or runner) and is tracked separately. Until it is fixed, the local fast tier and gates are the verification record.

**G5 gate fixture repaired (housekeeping, after G10.6).** `run_g5_human_biology_gate.py` had been failing `reproduction_occurred` and `birth_added_human` on `main` since the reproduction-contact correction (PR #23), hidden by the dead CI.
- Its birth probe placed the pair on the richest cell.
- The first adult's bite made a neighbour richer, so the second adult walked away before reproduction.
- The probe now uses a cell that stays the movement rule's choice after the earlier adults' bites. It tests reproduction, not whether the pair happens to stay together.

No model code changed. All 19 gate scripts pass.
