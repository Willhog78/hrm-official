# Plant decline: diagnosis and correction (2026-10-08)

## Question

Edible vegetation shrank every year in every daily world, including plant-only controls. Its yearly peaks were still falling 20–30% a year at year 10.

The owner asked for a concrete decision: is this an implementation defect, an initial boom settling down, or rules that cannot sustain vegetation under the generated climate? Then fix the demonstrated cause, without raising growth simply to guarantee survival.

## Measurements

All are read-only, with the ledger digest identical to an unobserved run:
- `qualification/genesis/plant_balance.py`;
- the plant ledger;
- local water-budget and scale checks.

The world is the plant-only control (seeds a and d, 10 years, 365 days/year).

1. **The climate is stationary.**
   - `world/climate.py` and `world/energy.py` are a fixed seasonal cycle plus noise, with no trend.
   - The light and temperature factors average 0.716 and 0.647–0.654 in every one of the 10 years.
2. **Water is what differs between years.** The water factor (soil water / 18 kg) averages 1.00 in year 1, then 0.76, 0.54, 0.62, 0.76, … 0.85.

   | Year (seed d) | Condition | Water factor | Growth limited by water (growth-weighted) |
   |---|---|---|---|
   | 1 | 0.626 | 1.00 | 0% |
   | 2 | 0.46 | 0.76 | 17% |
   | 3 | 0.328 | 0.54 | 18% |
   | 10 | 0.53 | 0.85 | 23% |

3. **Not old age, soil elements, or a conservation error.**
   - The old-age mortality term causes 0.0% of deaths in every year.
   - Growth receives 96–100% of what it asks for, so soil elements are not limiting.
   - No water is created by the soil clamp (0 t every year).
4. **The water budget does not balance at the production scale.**

   | Year (control a) | Rain | Transpiration | Water store at year end |
   |---|---|---|---|
   | start | — | — | 13,568 t |
   | 1 | 104 t | 1,998 t | 11,667 t |
   | 2 | 105 t | 4,793 t | 6,972 t |
   | 5 | 105 t | 807 t | 3,832 t |
   | 10 | 104 t | 128 t | 2,945 t |

   The vegetation is shrinking toward the size that 104 t of rain a year can supply.
5. **The same rules in a unit-consistent world sustain vegetation.** At material scale 1 the same seed, climate and plant rules give:
   - edible peaks of 0.37, 1.29, 1.57, 1.71, 1.75 kg, then 1.79–1.84 kg in years 6–10;
   - steady soil water and no dry cells.

## Decision: implementation defect

G10.1 (`G10_1_SCALE_SUBSTRATE.md`) scales the **inventories** by `material_scale_factor` (1000 in every Agentus world): soil elements, soil and surface water (45 t and 8 t per cell), and initial plant biomass. Plants grow in proportion to their own mass, so their water demand (2.5 kg per kg of growth) scales too.

The water cycle's **fluxes and capacities were never scaled**, and they remain in scale-1 kilograms:
- rain per event (0.5–5 kg);
- infiltration (3 kg/day);
- soil capacity (100 kg);
- evaporation (0.03 × solar + 0.004 × temperature kg/day);
- the runoff residue (0.5 kg);
- the plants' water threshold (18 kg).

The consequences:
- **Year 1's boom is the scaled initial reservoir being spent.** Infiltration is blocked while soil water sits above the unscaled 100 kg capacity.
- **The later decline is the plants converging on the unscaled rainfall,** about 1/1000 of what the scaled world needs.

G10.1's own exit condition ("retain plants") is therefore violated over multiple years. Its gate (`run_g10_1_scale_gate.py`) runs 24 monthly ticks, which is too short for the reservoir to run down.

It is not an initial boom settling to a sustainable level: the level it settles toward is set by the unit error. And the plant rules can sustain vegetation under the generated climate (finding 5).

## Correction (`water_cycle_scale = "material-v1"`, default)

- **What scales.** Everything listed above is multiplied by the stored `water_scale` (= `material_scale_factor`): rain entering the soil and surface, the infiltration cap, the soil capacity, evaporation, the runoff residue and the plants' 18 kg water threshold.
- **What stays the same.**
  - The world's climate fields (`precipitation`, which fire also reads) are unchanged.
  - The water cycle is linear in these quantities, so a scaled world is the unit world multiplied by the scale (`tests/genesis/test_water_cycle_scale.py`).
- **No change at scale 1.** `water_scale` is stored, and the fingerprint key `water_cycle_scale` added, only when the scale is not 1. G0–G9 runs at scale 1 are untouched.
- **Legacy.** `unscaled-legacy` (arm suffix `-legacywater`) reproduces the previous commit's digest and fingerprint exactly. Checked: seed a, 300 days, `d4c010e6…` in both.
- **Plant rates are not changed.** Growth is not raised.

## Validation (plant-only control, corrected, scale 1000, 10 years)

| | Year 5 peak / year-end | Year 10 peak / year-end | Years 7–10 peaks |
|---|---|---|---|
| Scale 1 (× 1000) | 1,753 / 765 t | 1,826 / 817 t | 1,818–1,838 t |
| Corrected, seed a | 1,724 / 771 t | 1,822 / 823 t | 1,809–1,834 t |
| Corrected, seed d | 1,753 / 780 t | 1,842 / 832 t | 1,820–1,852 t |

- Soil water is steady at about 25,000 t, and no cell is dry in any year.
- Years 1–2 differ from scale 1, because a few plant thresholds are still unscaled (below). The trajectories converge from year 3.

## Not changed (not demonstrated causes)

- **Plant thresholds still in scale-1 kilograms:** the minimum germinating seed mass (2 g), the minimum seeding biomass (20 g) and the minimum fire fuel (50 g). They affect early years only (validation above).
- **Animal scale** (G10.3 / G10.4 open decision).
- **The child energy clamp** (`DEMAND_LIMITED_MILK.md` §7): a separate correction.
- **Plant growth and mortality rates.**

## Scope of the claim (owner qualifications, 2026-10-08)

- **The water cycle scales exactly, but the ecosystem does not.**
  - The test proves that the water cycle at scale *k* is the unit water cycle × *k*.
  - The whole ecosystem does not scale exactly. Three plant thresholds (germination, seeding, fire fuel) and animal body sizes are still in scale-1 units.
- **Plants persist; a self-sustaining inhabited world is not yet shown.** The stable plant-only vegetation shows that plants can persist under the generated climate. It does not establish a self-sustaining inhabited world. That needs the inhabited runs, and generations beyond the founders.
