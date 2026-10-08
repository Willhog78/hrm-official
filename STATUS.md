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

- Stage-1 coordination regression suite: **43/43 PASS**, originally run via a minimal pytest stand-in because pytest was unavailable on that host. Every correction's test was shown to fail with that correction removed.
- **Real pytest run (2026-10-07):** `tests/test_stage1_coordination.py` **43 passed**, `tests/test_stage1_hmt_contract.py` **14 passed**. Commit `4fd0224`, Python 3.13.16, pytest 9.1.1; exact commands in `evidence/STAGE1_PYTEST_RUN_2026-10-07.md`. The coordination suite also passed under Python 3.11.17 (the version CI pins), in the local workflow-step run under "Verification infrastructure".
- HMT Stage-1 Gate: **14/14 PASS as one monolithic run** (≈36 s).
- `qualification/reproduce_stage1.py`: without the `UPSTREAM/` Agentus archive (not in the repository) it skips the Agentus step, prints `STAGE1_REPRODUCTION_PARTIAL (S1.12 not evidenced)` and exits 2. `--require-upstream` fails immediately if the archive is absent.

**Why Stage 1 is still not frozen:**

- S1.12 is unevidenced until the archive is supplied;
- three reported risks are untested: non-atomic checkpoint writes, unbounded publish bookkeeping, and undetectable genesis tampering with an empty ledger;
- no automated (CI) verification has ever run (see "Verification infrastructure").

The real pytest run cleared the "no real pytest run" blocker. Clearing that one item does not freeze Stage 1.

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
- G10.2 calibrated reference humans;
- G10.2A survival affordances (PR #19): terrain-conditioned rock/cave cover and condition-grown woody biomass;
- G10.3–G10.6 and G10.7a steps 1–4 (sections below).

Long-run calibrated-human survival is **not qualified**. Under the advancement rule (see "Testing tiers"), survival is reported, not used as a gate.

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

**G10.7a step 1 (leak closure): IMPLEMENTED** (`docs/architecture/G10_7_COMMUNICATION_TEACHING.md`, flag `agentus_observation_model`, default `visible-v1`; `g10.4-legacy` is bit-identical to before).
- G7 recipe transfer works only with a legacy flag.
- Observers get visible acts and consequences, appraised by their own values.
- Seen eating changes only readiness to taste.
- Legacy food adoptions fell from 11 to 0, as expected.

**G10.7a steps 2–4: IMPLEMENTED** (PRs #30–#33). Specification and evidence are in `docs/architecture/G10_7_COMMUNICATION_TEACHING.md`, sections 6–9.
- Step 2: witnessed-event memory.
- Step 2.5: retention by visible consequence.
- Step 3: imitation as a bias on what to try.
- Step 4: following, learned from the agent's own experience.

In the targeted diagnostics, step 3 produced 7 imitated tries, none of which paid, and following never occurred.

**COGNITION WORK PAUSED (owner decision, 2026-10-07).** G10.7a step 5 (measurement) and G10.7b (the costly call) do not start until the ecology question has been tested. The question: which condition keeps social learning from having an opportunity? The candidates are measured separately:
- hunger;
- no reachable known food;
- another agent nearby;
- a useful act witnessed.

Opening, census and controlled-experiment proposal: `docs/architecture/ECOLOGY_OPPORTUNITY_OPENING.md`. The next milestone is an explanation of the missing opportunities. That explanation may be that these mechanisms have little value in this world.

**D2 consumer timebase correction: IMPLEMENTED (owner-authorized 2026-10-07).** Specification and validation: `docs/architecture/D2_CONSUMER_TIMEBASE.md`. Flag `consumer_timebase`: default `elapsed-time-v1`; `per-tick-legacy` reproduces earlier runs exactly.
- **What it fixes.** Animal rates stated per month (metabolism, water loss, bite, carcass decay) are now converted to the tick length, as durations already were. Before, daily-tick worlds charged a month's rate every day.
- **Unchanged.** 12 ticks/year runs, including G4, are bit-identical.
- **At daily ticks:**
  - the predator survives for years instead of weeks;
  - herbivore births are unchanged, so the life-history bottleneck stands as a calibration issue;
  - Agentus injury deaths rose from 2 to 7 in the two-year census.
- **Verification.** 9 equivalence tests pass, all 19 gates pass, micro passes, and smoke shows 0 fail and 0 warn. One test horizon was restated in simulated years.
- **Not done.** Life-history recalibration is not done and needs separate authorization.

**Open owner decisions:**
- **D1:** predation on Agentus is an unresolved rule, now split into three questions (hunt living Agentus, consume dead Agentus, defensive injury; none authorizes cannibalism). It is active, because predators survive and bite.
- **D3:** default physiology stays `reference-v1` until the caregiver energy budget closes.

**Caregiver energy budget and imitation audit: DONE (2026-10-08, diagnostics only; no model change).** Report: `experiments/genesis/summaries/BUDGET_AND_IMITATION_AUDIT_2026-10-08.md`; tool `qualification/genesis/budget_audit.py`, read-only and digest-checked.
- **Caregiver deficit (reference-v2).** The deficit is milk for two overlapping dependents on a full gut. The energy ledger closes to 5e-11 kcal per agent-day.
  - 100% of the deepest days (reserve below 0.25) have two dependents.
  - The gut is full and food is in the cell on all of them.
  - Movement, temperature and effort are negligible.

  Under v1, caregivers break even. Their few losses are days the gut was not filled.
- **Imitation.** All 72 copied tries (18 pre-D2, 11 v1, 43 v2) were scored on effort alone.
  - 71 were preparation acts, whose same-day reward excludes everything but food from a capture or cut.
  - The one cut exposed meat that the sated agent did not eat.
  - The delayed routes deliver nothing in two years: 0 kcal of warmth saved, no worn surfaces, and ≤0.06 kg of meat per seed.
  - Imitators had always seen matter change, never anyone eat.

  This does not show that imitation generally fails.
- **Injury deaths.** Cause tracking attributes all of them (v1: 7; v2: 8; pre-D2: 2) to the unprovoked, foodless predator bite.

**Encounter frequency (open).** At daily ticks, animals travel 25–80× farther per year and predators make about 14× more hunt attempts than at monthly ticks (D2 note, section 8). Predator-related mortality is not interpreted as ecologically calibrated until this is decided.

Ecology experiments E1–E3 stay unimplemented. Physiology and life-history values are unchanged.

## Verification infrastructure

**CI has never run.** All 119 runs of the GitHub Actions `Stage-1 verification` workflow have failed in about 3 s, before a runner was assigned. That covers runs 1–119, from the first run on 2026-09-23 to the merge of PR #33. No log exists. GitHub's annotation on the job (checked for runs 1, 11 and 119) says:

> The job was not started because your account is locked due to a billing issue.

The earlier note that it failed "since runs 99–104" was wrong. No CI result exists for any commit.

**To restore it:**
1. The account owner resolves the billing lock under GitHub *Settings → Billing and plans*. Nothing in the repository can fix this. For a public repository, standard GitHub-hosted runners are free, but a locked account still blocks them.
2. Re-run the latest `main` workflow to confirm that a runner is assigned.
3. Bring `.github/workflows/stage1.yml` up to date before relying on it. It stops at the G10.2 gate and omits:
   - the G10.2A, development, conditional-adaptation, physical-interaction, predator and weather-persistence gates;
   - the micro and smoke tiers.
4. Note: `ubuntu-latest` moves to Ubuntu 26 from 2026-10-19 (GitHub notice on the same jobs).

**Local run of the workflow's steps under Python 3.11 (2026-10-07).** Every step in `stage1.yml` passed. The steps were run serially with Python 3.11.17 and pytest 9.1.1 on an otherwise idle 4-CPU container, at commit `4fd0224` plus this branch's census files:

| Step | Seconds |
|---|---|
| Stage-1 regression suite (43 tests) | 1.1 |
| HMT Stage-1 Gate | 43.2 |
| Genesis regression suite (`tests/genesis`) | 564.3 |
| G4 autonomy gate | 228.6 |
| other 13 gates and Stage-2 draft suite, combined | 92.1 |
| **total** | **924.8 (15.4 min)** |

The six gates not in the workflow also pass, together in under 3 s.

This run also covers Python 3.11 for the Stage-1 tests. The 20-minute job timeout is not yet established either way:
- the steps above took 15.4 min on this host;
- checkout, Python setup and `pip install` are not included;
- GitHub-hosted runner speed was not measured.

The first real CI run will settle it. If it is tight, splitting the Genesis suite and the G4 gate into their own jobs removes the risk.

Until CI runs, the local tiers and gate scripts are the only verification record. Because nothing runs automatically, a failure can sit unnoticed on `main`. The G5 gate failure below is the example.

**G5 gate fixture repaired (housekeeping, after G10.6).** `run_g5_human_biology_gate.py` had been failing `reproduction_occurred` and `birth_added_human` on `main` since the reproduction-contact correction (PR #23), hidden by the dead CI.
- Its birth probe placed the pair on the richest cell.
- The first adult's bite made a neighbour richer, so the second adult walked away before reproduction.
- The probe now uses a cell that stays the movement rule's choice after the earlier adults' bites. It tests reproduction, not whether the pair happens to stay together.

No model code changed. All 19 gate scripts pass.
