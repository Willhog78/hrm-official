# Gate 0 — Consequential weather, exposure, and animal materials (inspection record)

Date: 2026-10-09. Status: **PARTIAL INSPECTION; IMPLEMENTATION BLOCKED until remaining checks complete.** This is an evidence/provenance record, not a declaration that any requested physical gate passed.

## Branch ancestry and review target
- Repository default: `main`.
- PR #34 merged into `ccr-12877dfd-gxegwl`, merge commit `646ef3f96e82928e7618196bf8df8272d7e28167`; not into main.
- PR #35 merged into `codex/30-year-diagnosis`, merge commit `54eee90122d5a8c57e8ccfc513f778b51390d718`; not into main.
- Working branch `codex/genesis-consequential-exposure-materials` was created from `codex/30-year-diagnosis` to retain the merged #35 nursing work. Do not silently retarget to main or presume #35 is included in the older ccr branch.
- `AGENTS.md` was absent at the inspected branch root (GitHub returned 404). Search for nested agent rules before making implementation edits.

## Verified code ownership / current behavior
- `src/hrm_genesis/world/climate.py` computes seeded temperature, precipitation, persistent anomalies and lightning. `world/state.py` writes these per cell. No explicit wind or snow in inspected climate/world state.
- `matter/transfers.py` owns the rain -> surface -> soil -> runoff/evaporation water cycle and cumulative precipitation/evaporation ledger. Snow and body/material wetness would need explicit transfer boundaries.
- `human/biology.py` contains `_structural_protection`, `_apply_physiology`, `_experienced_reward`, and human state creation. Current arrangement protection multiplies geometry and area but applies only a zero/nonzero check to arranged mass. Terrain/canopy moderate effective ambient temperature; worn insulation adds degrees to effective ambient rather than balancing heat flux. Thermal energy cost, water loss, severe-exposure injury and a bounded core-temperature estimate exist. There is no demonstrated persistent wetness or physiological cold/heat debt.
- `human/interactions.py` contains in-cell affordance enumeration, grasp/carried objects, force interactions, learned values, eligibility trace, witnessed memory and imitation. Current surface insulation derives from worn surface area and cohesion. `weather_objects` decomposes organic objects, transfers their elements into detritus, and applies fire damage/stone heating.
- `matter/objects.py` owns stone properties/fracture/edge wear, fibers, wood, interlacing and bindings. Reuse primitive force and contact mechanics; do not introduce a named bone-tool recipe.
- `ecology/animals.py` `kill_animal` removes animals once and transfers full tracked body elemental mass to pooled fresh/legacy carcass tissue and water to carcass water. `consumer_element_totals` counts living animals and both carcass pools. Current carcass pools cannot identify individual historical skeletons or hides; backfilling those parts would fabricate information.
- `config.py` stores explicit switches with checkpoint fingerprint effects; `checkpoint.py` rejects incompatible configuration fingerprints and delegates state persistence to Stage-1 coordination.

## Dependency map
Climate/world fields -> matter hydrology -> producer fire/detritus/material geometry -> ecology carcasses -> human body + carried/arranged objects + sensation/learning -> read-only observer. Keep world state, matter state, animal state and human state under their current owners and pass effects through existing interfaces. Add state migration/initialization logic only where the saved-state boundary demands it.

## Physical invariants to enforce
1. Precipitation is an accounted open-system water input; evapotranspiration is an accounted output; rain, snow, meltwater, body/material wetness and water pools cannot duplicate water.
2. Every deceased animal transfers tracked elements and water once; partitions into soft tissue, bone, marrow, hide/fur and tendons must sum to the original animal's accounted mass/elements.
3. Removing or burning an arrangement or pelt must decrease both the object's conserved elemental inventory and its effective protective properties.
4. Thermal energy debits count once; sweat/evaporated body moisture uses explicitly accounted water. Cold/heat strain is stateful and reversible when physically appropriate.
5. Existing seed/config/state combinations remain replayable in an explicitly labeled legacy mode. Never infer anatomy or prior exposure from historical aggregate remains.
6. Observers measure without affecting world state, action choices, rewards or random streams.

## Risk assessment
**High:** changing climate/hydrology and thermoregulation simultaneously risks water/energy double counting, changing death classification, and invalidating historical checkpoints.
**High:** existing animal deaths lose individual body anatomy inside cell pools, so old remains cannot be decomposed retroactively into individual bones/hides.
**High:** arrangement geometry currently has a nonphysical tiny-mass loophole; closing it changes survival outcomes even without agent decisions.
**Medium:** attributing later exposure relief to a particular action can reward unrelated acts; eligibility and causal position must be checked before learning.
**Medium:** base ancestry diverges from `main`, and #34/#35 merged into different non-default branches.
**Medium:** no local executable checkout/test runner was available at inspection time; no baseline pass counts or replay claims are asserted.

## Smallest proposed implementation surface and sequence
1. Finish reading geometry setters, existing fire/carcass/physiology/learning pathways, production runner and all applicable nested rules; establish tests and integration ancestry.
2. Gate 1: `human/biology.py` + geometry object logic where needed + focused tests; protection must be driven by surviving volume, coverage, orientation, position and damage.
3. Gate 2: `world/climate.py`, `world/state.py`, `matter/transfers.py`, `human/biology.py`, minimal linked interaction/state plumbing and tests. Add explicit units, flux ledgers and legacy switch.
4. Gate 3: `ecology/animals.py`, `matter/objects.py`, `human/interactions.py`, focused transfer and checkpoint tests.
5. Gate 4: same material/interaction paths and controlled physiology/decay coupling.
6. Gate 5: human perception/learning and read-only diagnostics, deterministic bounded local comparisons. Railway remains untouched.

## Gate status / limitations
Gate 0 **not passed yet**: no verified baseline suite, exhaustive production settings, full save-state schema and action/cognition/fire ownership trace. Gates 1–5 must not be described as implemented, tested, observed or learned. No full Railway experiment, deploy or merge authorized.

## Gate 0 continuation — primitive geometry and deployment inspection
- `human/actions.py::execute_live_sequence` transfers woody elements among woody, held, loose and arranged pools. `arrange` increases span by a fixed +0.45 m, height by +0.20 m and surface area by +0.5 m² per action even for arbitrarily small positive transferred mass. `separate` removes arranged mass without reducing stored geometry. `combine` transfers loose to arranged without updating geometry. These are direct physical consistency defects, requiring coordinated fixes with `biology._structural_protection` rather than changing only an insulation coefficient.
- The current `biology._apply_physiology` charges thermal energy once and draws water for heat, followed later by a separate basal water loss recorded to `matter.water_output_kg`. The thermal water loss is not visibly added to that output in the inspected method. A conservation-focused test must verify this before Gate 2.
- The default `GenesisConfig` uses 120 ticks/year and disabled human/ecology; a calibrated long run explicitly enables 365 ticks/year, material scale 1000 and human actions/cognition. Any new duration/rate must scale with simulated elapsed time, not blindly with tick count.
- Root `AGENTS.md` is absent; other repository rules still apply. The tree also lists multiple *planned* files; do not treat them as present or import them.
- Baseline tests **not run**: the available shell environment could not resolve github.com and therefore could not clone this repository. GitHub connector reads and writes work; they do not execute the project tests. This is an unresolved Gate 0 verification requirement, not a passing result.

**Additional risk:** changing arrangement geometry setters and ambient moderation at the same time could confound protection contrasts. The minimal Gate 1 should first make geometry mass-constrained and damage-aware with a legacy-controlled opt-in, then measure resulting cover independently of thermal physiology.

## Gate 0 final ownership, transfers, and replay findings
- `runner.py` instantiates independently owned world, matter, producer, consumer and human authorities; the human tick can atomically alter producer, matter and consumer states. Clock, schedules and replay ledger live under Stage-1 coordination, not observer state.
- **Climate / weather:** `climate.py` deterministically provides temperature, precipitation, lightning, slow anomalies; `world/state.py` persists per-cell forcing. `matter/transfers.py` credits precipitation to water_input_kg and debits evaporation to water_output_kg, with local surface/soil exchange and runoff. Neither wind nor frozen water/snow state exists in these inspected ownership paths.
- **Heat / fire:** `ecology/plants.py` ignites burnable woody/loose/arranged material from lightning, applies rain quenching, and spreads to adjacent cells without direction. Burned tracked elements are returned to producer detritus. `human/interactions.py::weather_objects` also burns/degrades organic objects into detritus. Fire-induced material loss therefore changes mass pools but currently can leave arrangement geometry unchanged.
- **Physiological water accounting confirmed:** `_apply_physiology` reduces body_water_kg for high thermal exposure; `evolve_agentus_step` separately subtracts basal loss and credits ONLY that latter loss to `matter.water_output_kg`. The thermal decrement requires explicitly accounted output in Gate 2. Basal energy, movement, interaction and thermal costs are separately debited; Gate 2 must replace rather than stack heat-transfer costs.
- **Carcasses:** `animals.kill_animal` transfers each killed animal's tracked elements and water into carcass pools once. Predation has its own prey-transfer path; `evolve_consumers` decomposes carcass elements into detritus and carcass water into Matter. Existing `consumer_element_totals` and `consumer_water_total_kg` are conservation checks to extend for new anatomy. Legacy aggregate carcasses have no per-animal provenance; they must remain unpartitioned.
- **Primitive interaction ownership:** `human/actions.py` owns `grasp, release, carry, combine, separate, apply_force, arrange` over woody pools. `human/interactions.py` owns physical `grasp_object`, release, striking, cutting, tendon extraction, pulling, interlacing, binding and wearing; `matter/objects.py` owns force/strength/fracture/edge mechanics. Reuse these verbs rather than adding named bone or clothing recipes.
- **Cognition:** `human/perception.py` exposes local temperature/material cues. `human/biology.py::_experienced_reward` credits energy/water and penalizes injury. `human/interactions.py::learn_from_tick` assigns direct interaction costs and realized eating benefits, maintains an eight-entry trace plus object history, and observes visible consequences. `imitation_candidate` uses witnessed events as trial bias; `credit_worn_benefit` separately credits realized thermal-energy savings. Existing delayed credit is food-specific and insufficient evidence for exposure-learning claims without an exposure-specific causal test.
- **Checkpoint/schema:** `GenesisConfig.canonical` and `fingerprint` preserve existing configuration provenance. `checkpoint.py` loads through Stage-1 and rejects mismatching fingerprints; `runner._from_restored` validates time-step and exact authority set. Opt-in flags and missing-key legacy behavior have existing precedents. A new weather/body/anatomy schema must explicitly document initial-state defaults, legacy-mode handling, and how unstructured historical pools stay unstructured; changing the fingerprint does not itself migrate data.
- **Production/run configuration:** `experiments/genesis/run_agentus_demography_multiseed.py` explicitly uses 16×16 cells, 365 ticks/year, scale 1000, cognition and actions enabled; runner defaults in `config.py` are NOT a production-equivalent Genesis long run. Railway runtime configuration remains untouched. Historical summaries are comparison records, not checkpoint proof of new physics.
- **Test inventory inspected:** `tests/genesis/test_survival_affordances.py` contains terrain-cover, plant production and protective heat-response tests; other relevant suites include `test_g10_3_agentus_capacities.py`, `test_g10_5_physiology.py`, `test_g10_7_memory_non_causal.py`, micro stone/fiber/learning/imitation/hunting tests, and `test_g1_5_matter.py`. These are candidate baselines, **not tests executed during this audit**.
- **Execution limitation:** a direct `git ls-remote` failed because the local executor cannot resolve github.com. GitHub connector can read and commit code but cannot execute Python; hence baseline passes/fails, current ledger digest and replay parity remain unknown. The current gate is closed for source audit, but **runtime sign-off is outstanding** and must occur before claiming Gate 1 validated.

## Gate 0 exit summary (plain English)
Identified all affected owner modules and the integration branch. Confirmed meaningful flaws in arrangement size vs actual wood, thermal water accounting, non-directional fire, and loss of animal anatomy in pooled carcasses. Confirmed reusable physical actions, reward traces, legacy configuration mechanisms and strict checkpoint fingerprinting. Documented transfer invariants, isolated implementation sequence and executable-baseline blocker. **Files changed:** this document only. **Physical capabilities:** unchanged. **Tests run:** 0 Python tests; 1 unsuccessful repository network access attempt. **Replay and conservation:** not executed, no pass claimed. **Observed Agentus behavior:** none newly observed. **PR:** draft #39; not merged.

## Uploaded main ZIP: executable baseline (2026-10-09)
The user supplied `hrm-official-main (1).zip` after the original audit. It is a local **main** export dated 2026-10-07, **not** a checkout of the PR #35 ancestry or this integration branch. It is valid as a baseline for the source contained in the archive, but cannot establish whether the #34/#35 fixes on the target branch pass tests.

Executed from the extracted tree with `PYTHONPATH=src:.`:
- `pytest -q tests/genesis/test_survival_affordances.py tests/genesis/test_g10_5_physiology.py tests/genesis/test_g1_5_matter.py tests/genesis/micro/test_micro_imitation.py`: **28 passed, 0 failed**.
- `pytest -q tests/genesis`: advanced to at least 155 passing progress indicators, then terminated by execution timeout; **incomplete, not a suite pass**. No failure trace was printed prior to timeout. Do not count this as validated completion.

Updated Gate 0 conclusion: executable baseline has been established for uploaded main, but the integration branch still needs its own complete set of targeted determinism, conservation, and replay checks. This is a precise revision to the earlier 'zero Python tests' note, not a claim that the historical source at the PR head was executed. No simulation code was changed during this audit.

## Gate 0 further executable local checks (uploaded main ZIP)
- Targeted run: `PYTHONPATH=src:. pytest -q tests/genesis/test_g0_integration.py tests/genesis/test_g1_5_matter.py tests/genesis/test_g9_observer_isolation.py tests/genesis/test_survival_affordances.py tests/genesis/test_g10_5_physiology.py tests/genesis/micro/test_micro_imitation.py --disable-warnings --maxfail=1`: **33 passed, zero failed** in the extracted uploaded main snapshot.
- Explicit 8-day calibrated Agentus + producer + consumer + cognition/action + capacity run, with a day-3 checkpoint resumed for five days: identical final ledger digest, human and Matter states; both replay chains verified. Two humans and four animals remained at end. This is a **short smoke**, not an ecological longevity or weather-exposure verification.
- `matter.accounting.water_balance_error` on this whole-biosphere configuration: **-80.242 kg**. That matter-only function measures the Matter authority reservoir and cannot by itself establish whole-world water loss once water resides in plants/animals/humans; the result requires cross-domain reconciliation. Do not report it as a confirmed leak or a pass.
- These tests exercise the uploaded **main** tree, not the #35 destination branch. Network `git ls-remote` remains unavailable (host resolution error), so source-specific branch parity and an integration-head test execution remain outstanding.

## Whole-system water balance reconciliation (uploaded main, 2026-10-09)
A fresh calibrated 4×4, 365-tick/year, scale-1000, capacity-enabled simulation was run for 8 daily ticks with simultaneous Matter, consumer and Agentus inventories. Calculation: `total_water(matter.cells) + consumer_water_total_kg(consumers) + human_water_total_kg(humans) - (matter.initial_water_kg + matter.water_input_kg - matter.water_output_kg)`. Initial error **0.0 kg**, and each day 1–8 **0.0 kg** to displayed six decimals. Matter-only errors (initial −84.581590 kg; later −80.650000 kg) exactly match water held in animals and humans. This explains the previously reported −80.242 kg Matter-only deficit in the other scenario as an expected ownership effect, though that exact earlier scenario was not independently rerun with a full inventory here. No whole-system leak detected in this short scenario. This is a baseline of uploaded `main`, NOT integration-branch validation or a proof that hot-weather evaporation is correctly accounted under the new model.

**Gate 0 outstanding:** tests still have not executed against the merged #35 target branch; a main ZIP cannot be represented as that branch. Branch-specific test execution remains a condition for complete Gate 0 sign-off. No Gate 1 code authorized by these checks yet.

## Additional local ZIP tests and branch parity limitation
- Reran six previously selected uploaded-main test files: **33 passed, 0 failed**.
- Ran `PYTHONPATH=src:. pytest -q tests/genesis/micro tests/genesis/test_g10_3_agentus_capacities.py tests/genesis/test_g7_actions_learning.py tests/genesis/test_g8_multi_population.py tests/genesis/test_g10_7_memory_non_causal.py --disable-warnings`: completed at 100% with only passing progress indicators (**124 dots, no failures reported**; command exit code 0). This expands local main baseline, but is NOT a runtime check of branch-specific changes.
- The uploaded ZIP lacks the new `tests/genesis/micro/test_micro_nursing_allocation.py` introduced on the post-main branch, so executing it in that tree fails with file-not-found. `git ls-remote` on github.com still fails DNS resolution in the local executor. Connector inspection confirms target branch ancestry, but there is no verified byte-for-byte local integration checkout. Therefore **Gate 0 branch-specific validation is still open**. Do not use main pass counts as evidence of #35 pass or certify Gate 0 as complete.
