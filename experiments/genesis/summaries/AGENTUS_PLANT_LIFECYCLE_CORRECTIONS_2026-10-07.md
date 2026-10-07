# Plant lifecycle corrections — October 7, 2026

This follows `AGENTUS_FOOD_INTAKE_DIAGNOSIS_2026-10-07.md`. Two plant-model defects were corrected one at a time. After each, the same four-seed, 730-day food intake experiment and its no-Agentus counterfactual were rerun.

Held fixed:
- starting resources and material scale;
- Agentus physiology, which includes bite cap, reserve, nursing and water;
- Agentus behavior;
- all other ecology constants.

Sustainable survival is an outcome to test here, not a target. Neither change was tuned against Agentus results.

## Change 1 — germination no longer rejuvenates established vegetation

**Defect.** Any germination set the cell's `age_ticks` to 0. Seed pools exceed the 0.002 kg germination mass almost everywhere after the first season, so cells were reset nearly every viable day. As a result, woody growth (which requires age ≥ 30) and plant old-age mortality effectively never acted.

**Correction** (`plants.py`, germination step). Cell age is now the biomass-weighted age of its vegetation. Seedlings enter at age 0 and dilute the age only by their share of live mass. An empty cell colonized by seedlings starts at age 0. Tests are in `tests/genesis/test_plant_lifecycle.py`. The previously failing `test_woody_biomass_requires_sustained_viable_growth_conditions` now passes.

**Result** (`agentus_food_intake_after_age_fix_2026-10-07.json`):

| | before | after change 1 |
|---|---:|---:|
| survivors at day 730 (A/B/C/D) | 0/0/0/0 | 0/0/0/0 |
| births | 13 | 18 |
| last death day | 425–447 | 510–714 |
| adult deaths | 32 energy | 32 energy |
| woody biomass max, with Agentus | ≤ 0.01 kg | 6.4–9.3 t |
| no-Agentus edible at day 729 | 8.5–10.6 t | 30–38 kg |

**What it exposed.** Aging now works, so all vegetation established at genesis ages together. Old-age mortality starts after 360 ticks. Recruitment of 0.002 kg per cell per day cannot renew cells holding about 100 kg each. In the no-Agentus run, the median live-cell age climbs past 360. Edible stock falls from 42 t (day 315) to 30 kg (day 729), while 61 t of seed sits ungerminated.

## Change 2 — seed turnover scales with the seed pool

**Defect.** Seed production is proportional to biomass (1.2% per viable tick). Germination was a fixed 0.002 kg per cell per tick regardless of pool size or world material scale.

No-Agentus seed A, measured before change 2:

| scale | typical live mass per cell | 0.002 kg as share of a cell's plants per day | seed pool at day 729 | edible at day 729 |
|---|---:|---:|---:|---:|
| 1 | about 0.5–3 kg | about 0.1–0.4% | 5.5 kg/cell | 91 kg total, persists |
| 1000 | about 100 kg | about 0.002% | 239 kg/cell (61 t) | 30 kg total, collapses |

**Correction.** Each viable tick, `max(0.002 kg, 1.65% of the seed pool)` germinates.
- **Small pools unchanged:** pools of 0.12 kg or less behave exactly as before.
- **Choice of 1.65%:** it is set from an ecological criterion, not from Agentus outcomes. At this rate, 95% of a seed cohort germinates within about 180 viable days, one growing season.

**Sensitivity check** (no-Agentus, seed A; edible at days 300 / 420 / 600 / 729, in t):

| fraction | day 300 | day 420 | day 600 | day 729 |
|---|---:|---:|---:|---:|
| 0.00825 | 91 | 31 | 227 | 13.3 |
| 0.0165 | 133 | 49 | 172 | 15.1 |
| 0.033 | 199 | 57 | 146 | 14.8 |

The qualitative outcome (a persistent producer ecology with a winter trough of tens of tonnes) does not depend on the exact fraction.

**Result** (`agentus_food_intake_after_seed_turnover_2026-10-07.json`):

| | after change 1 | after change 2 |
|---|---:|---:|
| survivors at day 730 (A/B/C/D) | 0/0/0/0 | 2/1/3/2 |
| births | 18 | 19 |
| adult deaths | 32 energy | 26 dehydration, 0 energy |
| dependent deaths | 16 dehydration, 1 energy, 1 injury | 11 dehydration, 6 energy |
| adult deaths before day 300 | 8 | 0 |
| adult days with reserve at capacity | 30.8% | 61.8% |
| second-year minimum edible stock, with Agentus | 34–74 kg | 12–19 t |

Food shortage is no longer a cause of adult death under fixed physiology.

**Not sustainable survival.** No surviving group has both an adult female and an adult male. Maturity is 18 years, so no child can replace a founder within the two-year horizon. Survivors are 6 founders (one female) and 2 dependent children.

## New failure exposed: adults dehydrate on transpiration-dried cells

All 26 adult deaths after change 2 fall on days 420–709, mostly in the second summer. Daily traces for seeds A and D (days 560–665) show the pattern:

- **Dry cells:** dying adults stand on cells whose soil plus surface water is exactly 0. Meanwhile the map-mean soil water is 22,000–34,000 kg per cell.
- **Cause of drying:** dense vegetation transpires 2.5 kg of water per kg of growth and drains its own cell. Mean soil water falls from about 34,000 to 22,000 kg per cell over the 100 days sampled.
- **Fire:** fire is present but mostly low intensity. Injury is near 0 in the traced deaths.
- **Planner:** it has no thirst input. Hunger is the only physiological signal it receives. Water enters its score as 0.002 × kg, and food dominates. Agents with full energy reserves stay on food-rich dry cells.
- **Time to death:** body water falls from 39.5 kg to the 21 kg death threshold in about 7–9 days without drinking.

This is both a behavioral and an ecological finding. It was not corrected here.

## Validation

- **Plant lifecycle tests:** 4 pass. Each fails with its correction removed.
- **Food intake diagnosis tests:** 2 pass.
- **Qualification gates on change 1:** G2, G4, G10.1, G10.2, G10.2A and Agentus development all PASS.
- **Qualification gates on change 2:** G2, G4, G10.1, G10.2, G10.2A and Agentus development all PASS.
- **`tests/genesis` on change 2:** only the 2 long-standing failures remain (consumer starvation fixture, observer snapshot fixture). The woody growth fixture failure is resolved by change 1.

## Next decisions (not made here)

1. **Thirst in planning.** Water need is not an input to planning. Exposing it, the way forage need already is, would be a behavioral correction.
2. **Transpiration.** Whether transpiration should be able to drive a cell's soil water to exactly 0, with no lateral recharge, is an ecological question.
3. **Growth cap.** With a working lifecycle, edible plus woody biomass grows to 150–300 t. A growth cap (density dependence) may now be warranted as a plant-model question.

Physiology is unchanged and should stay fixed while these are tested.
