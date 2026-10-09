# Nursing allocation counterfactual — 2026-10-09

Across four unchanged worlds over five years, infant deaths fell from three to zero with youngest-first, solids-before-milk allocation. Births increased from 39 to 44. This fixes a measured early-family allocation failure; it does not establish that all later infant deaths are eliminated.

## Mechanism and scope

New opt-in nursing model: `remaining-demand-v2`, available as observer/diagnostic arm `v1-remainingmilk`. The default `demand-limited-v1` and supply-capped legacy mode retain their prior behavior and configuration fingerprints. Railway remains on its existing configuration.

Caregivers act before dependents. Dependents act in ascending age, with IDs resolving ties, so milk-only infants receive milk before siblings old enough for complementary food. Children complete their existing self-feeding and caregiver solid-food transfer before nursing. Milk demand is the room remaining in the same bounded energy store after solid intake. Mothers pay the existing synthesis cost; existing supply limits, reserve floors, co-location guards, developmental dependence and mass/water transfers still apply. No new energy, food, omniscient food access, adult feeding capacity or reproduction rule is added.

Demand here means remaining **store capacity**, not a new biological daily intake target. This change does not revise the adult/child hunger-reference inconsistency, maternal reserve-floor calibration, carrying behavior, or feeding efficiency. Youngest-first allocation can disadvantage older children if solids are unavailable; scarce-family tests retain the supply constraint rather than guaranteeing survival.

Reordering children changes which child accesses shared food first and which individuals enter the reproduction survivor list first. Those are real counterfactual effects. No mating or kinship logic was changed. Milk mass and water now transfer after solid feeding together with milk energy, so their growth-related shortfalls are evaluated at that later point.

## Five-year comparison

Baseline parent: `14ae8514b1ce332a5b1d2577ce92cab5705b1abd`, carrying the completed run and read-only diagnosis. Seeds are `agentus-demography-a` through `d`, reference-v1 physiology. Each arm runs from initial state for 1,825 days; no production checkpoint is resumed.

| Seed | Old alive | Fixed alive | Old births | Fixed births | Old infant deaths | Fixed infant deaths |
|---|---:|---:|---:|---:|---:|---:|
| a | 15 | 16 | 7 | 8 | 0 | 0 |
| b | 17 | 19 | 10 | 11 | 1 | 0 |
| c | 12 | 13 | 4 | 5 | 0 | 0 |
| d | 24 | 28 | 18 | 20 | 2 | 0 |
| Total | 68 | 76 | 39 | 44 | 3 | 0 |

Baseline deaths reproduce the earlier diagnosis: seed b at age 44 days, seed d at ages 33 and 105 days. No deaths occur in the fixed five-year arms. Final animal populations match between arms in all four seeds. Higher maternal retained energy is consistent with the extra births; reproduction conditions were not modified. The result is a full-history counterfactual, not a paired trial that forces births to occur on the same days.

All 20 baseline yearly outcome records and all four baseline configuration fingerprints match the saved 30-year evidence. For each of the eight arm/seed runs, complete state parity with the canonical production scheduler passes for 30 days before instrumentation and again after callbacks and diagnostic acceleration. Long-run production ledger digests were not reconstructed. The replay uses exact private owned-state and animal-position acceleration, checked at annual boundaries.

## Validation

- Seven new allocation regressions pass: infant priority, solids reducing older-child milk, isolated infant survival, limited maternal supply, distinct fingerprints, and reference-v1/reference-v2 energy conversion and store bounds.
- Three-seed, 75-day fixed-arm smoke: zero failures, zero warnings, valid ledgers, maximum relative element balance error approximately 1e-15. Observed and unobserved ledger digests match.
- Full suite: 329 tests passed in 256.85 seconds. The suite collected the first four new regressions; the completed seven-test allocation file then passed separately, including three added coverage cases.
- The diagnostic observer now retains solid intake whether it precedes or follows nursing. This is an observation-only change. A final one-year fixed-arm observer check confirms parity and the same year-one outcome as the five-year comparison.

Evidence: `NURSING_ALLOCATION_2026-10-09_evidence.json` includes the eight arms' annual records, birth events, terminal infant traces, configuration fingerprints and smoke results. Five-year comparisons were launched before the observation-only food-trace enrichment; their survival results are unaffected. The final observer check is retained separately in that evidence.

## Reproduce

For each seed a, b, c and d:

```sh
python experiments/genesis/run_generations_diagnosis.py --seed b --arm v1 --years 5 --owned-state --spatial-index --out runs/nursing-baseline
python experiments/genesis/run_generations_diagnosis.py --seed b --arm v1-remainingmilk --years 5 --owned-state --spatial-index --out runs/nursing-fixed
python -m qualification.genesis.tiers smoke --arm v1-remainingmilk
python -m pytest
```

The next long experiment should select `remaining-demand-v2` explicitly and run through the late birth waves. Ten of the original thirteen infant fatalities happened after year five and are outside this comparison. The current baseline, checkpoints and Railway service remain available for that comparison.
