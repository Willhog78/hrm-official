# Agentus food intake and seasonal shortage diagnosis — October 7, 2026

This is a measurement-only experiment. No resource quantities, physiology calibration, ecology constants, or agent behavior were changed. It reruns the four seeds and 730 days from `AGENTUS_SURVIVAL_DIAGNOSIS_2026-10-07.md` at the corrected code (`d7bfbcc`).

**Result:** the Agentus collapse comes from how food is produced, not from how agents eat or move. Producer biomass grows purely exponentially with a long net-negative winter. Agentus feeding at the seasonal low point suppresses the next season roughly tenfold. By the second winter, almost no edible food remains anywhere on the map. Physiology then leaves almost no margin to bridge the gap.

## Method

`experiments/genesis/run_agentus_food_intake_diagnosis.py` wraps internal functions (`_eat`, `_apply_physiology`, `_provision_dependent`, `execute_live_sequence`, `_growth_limit`, and the producer, consumer and human steps). The wrappers only record values and return the original results unchanged. Nothing they record is passed to agents.

- **Read-only check:** all four seeds reproduce the prior corrected outcomes exactly: births 2/4/4/3, deaths 10/12/12/11, causes energy 32, dehydration 12, injury 1. All ledgers verified. `tests/genesis/test_food_intake_diagnosis.py` asserts that ledger digests match after 12 ticks with and without wrappers.
- **Budget check:** for each adult, intake − basal − movement − thermal − nursing equals the recorded energy change. The test asserts this closure.
- **Counterfactual:** the same seeds were run with the human authority disabled. This is not a resource change. The only difference at genesis is that founder bodies (216 kg) are not debited from plants.
- **Post-processing:** `findings` and the compacted daily series in `agentus_food_intake_diagnosis_2026-10-07.json` were produced by the script's `aggregate`/`_trim_daily` functions. These were applied to the same raw run output.

## 1. Daily intake: the bite cap binds, and the margin is small

These are pooled adult-days (9,454) across all four seeds. Need is 1.136 kg/day, and the most an adult can be credited is 2,376 kcal/day.

| per adult-day | value |
|---|---:|
| credited intake | 2,091 kcal |
| basal | 2,000 kcal |
| movement | 22 kcal |
| thermal | 4 kcal |
| nursing given | 88 kcal |
| reserve-saturation waste | 93 kcal |
| days limited by bite cap / by cell supply / no food on cell | 88.5% / 11.2% / 0.3% |
| days with reserve at capacity | 28.2% |

- **Maximum surplus:** 376 kcal/day over basal (bite cap 1.35 kg × 2,200 kcal/kg × 0.8 assimilation). Nursing at full dependence costs 350 kcal/day, which is 93% of that surplus.
- **Refill time:** a depleted reserve takes at least about 80 days of perfect feeding to refill.
- **Reserve size:** the reserve cap of 30,000 kcal is 15 days of basal. While food is plentiful, adults sit at the cap and waste food. An adult at full reserve dies within about 30 days once intake falls to about 0.65 kg/day.
- **Not material:** movement and thermal costs are about 1.3% of basal. Movement cost is not a material cause.

Seasonal adult intake (kcal/day, pooled across seeds):

| period | year 0 | year 1 |
|---|---:|---:|
| days 0–91 (cold) | 2,246 | 1,702 |
| days 91–182 | 1,997 (below basal) | — (extinct) |
| days 182–273 | 2,140 | — |
| days 273–365 (cold) | 2,126 | — |

## 2. Seasonal edible production: exponential and net-negative for 5–6 months

- **Growth limits:** soil nutrients and water never limit growth (0 limited cell-days; matter N is about 10⁶ kg). Growth is set only by `min(light, temperature, water)`, and temperature or light is always the binding factor.
- **Growth law:** growth is proportional to standing biomass, with no density dependence.
- **Break-even condition:** at the plants.py constants, a cell needs condition ≥ about 0.62 to break even, or about 0.71 when it also sheds seed.
- **Winter decline:** `experiments/genesis/run_producer_breakeven_sampling.py` samples seed A without Agentus every 30 days in year 2. The map-mean net rate turns negative between year-days 265 and 295 and stays negative until between year-days 85 and 115, about 5–6 months. No cell of 256 is net-positive at any sample from year-day 325 to 55, and the rate in that span is −2% to −5% per day. Temperature binds in 125–197 cells and light in the rest.
- **Grazing:** animals take about 0.01 kg/day in total, so herbivores are effectively absent as competitors.
- **Seed sink:** reproduction moves 1.2% of edible mass per day into seed. Germination returns at most 0.002 kg per cell per day. By day 729, inedible seed pools hold 6.8–8.7 t with Agentus and 84–114 t without, against 0.2–0.3 t and 8.5–10.6 t of edible biomass.
- **Woody biomass:** woody biomass stays effectively zero (≤ 0.01 kg) in every run. Germination resets cell age almost daily, so the `age ≥ 30` woody condition is rarely met. This matches the existing `test_woody_biomass_requires_sustained_viable_growth_conditions` failure. It also means the old-age plant mortality term does not act.

## 3. Feeding at the seasonal minimum suppresses later production

Edible stock, map-wide (kg):

| seed | day 120 with / without Agentus | day 300 with / without | day 420 with / without | cumulative intake by day 300 |
|---|---:|---:|---:|---:|
| A | 435 / 1,673 | 2,833 / 26,209 | 42 / 1,555 | 1,967 |
| B | 576 / 1,948 | 3,296 / 26,617 | 23 / 1,683 | 2,373 |
| C | 666 / 2,110 | 3,955 / 35,384 | 17 / 2,331 | 2,643 |
| D | 478 / 1,927 | 2,833 / 24,471 | 28 / 1,491 | 2,274 |

Agentus intake is 8–11% of gross plant growth over two years. However, the gap between the two runs grows from about 0.6 × cumulative intake at day 60 to about 1.1× at day 120 and about 10–12× at day 300.

At the winter minimum, about 8 adults eat 1–2% of the standing stock per day while plants are already losing 3–5% per day. Every kilogram removed then would have compounded through the growing season. The year-1 summer peak never recovers. Second-winter minimum stock is 12–27 kg map-wide, with 0–2 cells holding one adult-day of food.

## 4. Deaths, separated

- **Founders:** all 32 were adults, and all died of energy.
- **Children:** all 13 born died as dependents: 12 of dehydration and 1 of injury. Dependents only receive water through nursing. These deaths follow the loss or absence of the caregiver and are downstream of adult starvation. No child reached independent feeding.

Adult deaths came in two waves:

| | first year (days 102–175) | second winter (days 355–439) |
|---|---:|---:|
| deaths | 14 | 18 |
| mean intake over prior 30 days | 0.92 kg/day | 0.81 kg/day |
| mean net energy over prior 30 days | −630 kcal/day | −776 kcal/day |
| 30-day window started at full reserve | 1 | 9 |
| final day: viable cell within 3 steps | 8 | 3 |
| final day: no viable cell anywhere on map | 0 | 9 |

- **First wave:** this is an access failure under local depletion. Food adequate for a day still existed within 3 steps for most of these agents. Their one-step perception and local search did not reach it before reserves ran out.
- **Second wave:** this is absolute shortage. Half of these agents entered their final 30 days with full reserves, and half died with no viable cell anywhere.

## Conclusions

1. **Main driver:** the dominant cause of collapse is the producer model's seasonal dynamics combined with harvest at the seasonal minimum. No foraging change can supply food that does not exist in the second winter.
2. **Physiology margin:** the bite cap and reserve size leave no capacity to bank food against a shortage of more than about 30 days. Nursing consumes almost the whole surplus.
3. **Behavior:** this matters only for the first wave. Food within 3 steps went unreached in 8 of 14 first-wave deaths.
4. **Ruled out:** movement cost, thermal cost, animal grazing, and soil nutrient or water limits are not material.

## Decisions required before further changes (not made here)

Each of these changes resources or calibration, which this experiment held fixed:

- **Producer regulation:** add density dependence (carrying capacity), or recalibrate the winter mortality-versus-growth balance.
- **Seed:** decide whether seed should be edible, or germinate in proportion to the seed pool rather than a fixed 0.002 kg per cell per day.
- **Germination age reset:** decide whether germination should reset cell age. Changing it would affect woody biomass and the G10.2A affordance claim, plus plant old-age mortality.
- **Adult physiology:** revisit bite cap, reserve capacity, and the nursing burden relative to the 376 kcal/day maximum surplus.

## Reproduce

```
PYTHONPATH=src python3 experiments/genesis/run_agentus_food_intake_diagnosis.py --out food.json   # about 8 min on 4 cores
PYTHONPATH=src:. python3 experiments/genesis/run_producer_breakeven_sampling.py                    # about 2.5 min
```

## Validation

- `tests/genesis`: 47 passed, 3 failed. The 3 failures (consumer starvation fixture, observer snapshot fixture, woody growth fixture) are the same pre-existing failures recorded in the October 7 survival diagnosis. This change touches no `src/` code.
- `tests/genesis/test_food_intake_diagnosis.py`: 2 passed. These cover wrapper read-only behavior and restore, and adult energy budget closure.

Sustainable-survival qualification remains blocked.
