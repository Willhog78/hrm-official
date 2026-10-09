# Daily world, 5 years, 4 seeds (Railway, commit 36f28ce, 2026-10-08)

## Setup

- Arm `v1`, 365 days per year, physiology `reference-v1`.
- Consumers `elapsed-time-v2`, plants `elapsed-time-v1`, caregiving `solid-food-v1`.
- Nursing was **supply-capped**. This run predates demand-limited milk (`docs/architecture/DEMAND_LIMITED_MILK.md`).
- Nothing was tuned or injected.
- Every ledger is valid. The audit closes the energy budget to 5e-11 kcal, and every check passed.
- Sources: Railway service `hrm-world-runner`, deployment `34112dc4`, logs only.

## Families

| Seed | Births | Survived to 1 year | Survived to 2 years | Child deaths | Alive at end of year 5 |
|---|---|---|---|---|---|
| a | 12 | 10/10 | 8/8 | 1 (energy, year 5) | 19 (8 adults, 11 dependents) |
| b | 8 | 6/6 | 5/5 | 0 | 16 (8 adults, 8 dependents) |
| c | 11 | 7/8 | 7/7 | 1 (energy, year 5) | 18 (8 adults, 10 dependents) |
| d | 9 | 9/9 | 7/7 | 0 | 17 (8 adults, 9 dependents) |

- Adults are still the 8 founders; the highest generation is 1.
- Five years cannot establish whether generations continue. The first children reach maturity at 18.

## Hand-feeding outcomes, by year

The counts are failure reasons from `capacity_stats.solid_food_outcomes`.

| Seed | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|---|---|---|---|---|---|
| a | too_young 720, not_hungry 129 | 342 / 1465 | 201 / 2172 | 537 / 2878, fed 9 (1.8 kg seed) | 223 / 3647, fed 3 (1.2 kg) |
| b | 490 / 166 | 410 / 1198 | not_hungry 1825 | 180 / 1935, fed 1 (0.27 kg) | 270 / 2304, fed 2 (0.66 kg) |
| c | 357 / 145 | 329 / 727 | 374 / 1426 | 315 / 2355 | 379 / 2716 |
| d | 708 / 385 | 355 / 1452 | 191 / 2171, fed 2 (0.55 kg) | 153 / 2549 | 213 / 3043, fed 24 (8.5 kg), gut_full 3, no_known_food_here 2 |

In the year 2–5 cells, the pair `x / y` is `too_young / not_hungry`.

- The children past 180 days almost always fail the hunger trigger: their reserve is at or above 0.75.
- `not_together` never occurs.
- `no_known_food_here` and `gut_full` are rare.

Whether milk is what keeps them above the trigger while their caregivers run down is the hypothesis the next run tests. The audit records the caregiver's reserve with each check.

## Caregiver energy (audit, mean kcal per caregiver-day)

| Seed | Caregiver days | Milk paid | Milk absorbed | Days reserve < 0.75 | Days reserve < 0.25 | Reserve < 0.25: milk paid / absorbed |
|---|---|---|---|---|---|---|
| a | — | 806 | 230 | 1533 | 710 | — |
| b | 6414 | 392 | 141 | 527 | 0 | — |
| c | 5938 | 463 | 198 | 936 | 380 | 798 / 247 |
| d | 6933 | 461 | 175 | 463 | 37 | 350 / 269 |

- On the days caregivers were short of reserves, their stomachs were full on 96–100% of days, with food in their own cell.
- The shortfall is milk paid for but not absorbed. That is the defect demand-limited milk removes.

## Adults without dependents

- They eat a full stomach every day, about 2040 kcal credited.
- Their reserve is full, so about 720–755 kcal/day of the energy offered by food is refused.
- That is unused intake, not a deficit. The next audit converts it to kg eaten beyond need, because that mass leaves the plant stock.

## Animals (year-end counts)

| Seed | Year 1 | Year 5 | Killed by Agentus over 5 years |
|---|---|---|---|
| a | browser 2, stalker 1 | browser 5 | 4 (grazers gone in year 1) |
| b | browser 2, grazer 1 | browser 4, grazer 1 | 5 |
| c | browser 2, grazer 1, stalker 1 | browser 3, grazer 2 | 3 |
| d | browser 2, grazer 2, stalker 1 | browser 1, grazer 2 | 7 |

- Hunting removes grazers entirely in seed a, and keeps them at 1–2 elsewhere.
- Predator attacks on Agentus: 0–2 per year.
- This needs tracking over the next run, without guaranteeing that any species survives.

## Learned behaviour

- 86–264 objects exist by year 5: cords, edged stones, sticks, and stick-and-stone bindings.
- None is worn, and no object use has a demonstrated payoff.
- Imitation: 0–6 tries per year, none paid off.
- In seed d, years 4–5, a few acts show positive learned value (binding, striking with a bound stone, stripping bark). Nothing traces them to a real benefit, so this is an observation, not a credited result.

## Plants

Year-end edible mass (t):

| Seed | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 |
|---|---|---|---|---|---|
| a | 45.1 | 17.4 | 7.4 | 5.3 | 1.8 |
| b | 47.9 | 19.6 | 6.8 | 3.7 | 1.5 |
| c | 59.3 | 16.1 | 7.4 | 4.2 | 1.4 |
| d | 48.3 | 17.2 | 7.9 | 4.4 | 1.4 |

These are single-day snapshots.

A ledger check after this run (seed a, first 2 years) found:
- Edible mass swings more than 10× within a year. In year 2 it peaks at 229 t on day 605 and falls to 17 t by day 730.
- A plant-only control falls the same way, from 86 t at the end of year 1 to 15 t at the end of year 2.

So the year-end series alone does not establish a cause, nor whether the decline continues. The plant ledger in the next run records growth, mortality, germination, seeding, animal and Agentus removal monthly, alongside a matching control with no consumers.

---

# Second run: demand-limited milk, plant ledger, plant-only control (Railway, commit 635c2ac)

## Setup

- Settings are the same as the first run, except nursing is `demand-limited-v1`.
- Every ledger is valid. The energy budget closes to 5e-11 kcal. The plant ledger residual is 0 for every pool, every year.
- Deployment `d51d76a2`, 2026-10-08, 09:03–10:34 UTC.

## Families (5 years)

| Seed | Births | Survived to 1 year | Survived to 2 years | Deaths | Alive at end of year 5 | Caregiver days | Reserve < 0.75 | Reserve < 0.25 |
|---|---|---|---|---|---|---|---|---|
| a | 11 | 10/10 | 9/9 | 0 | 19 | 6689 | 426 | 11 |
| b | 9 | 8/8 | 7/7 | 0 | 17 | 6409 | 143 | 0 |
| c | 4 | 3/3 | 3/3 | 0 | 12 | 3422 | 85 | 0 |
| d | 11 | 10/10 | 8/8 | 0 | 19 | 6917 | 153 | 28 |

- Caregivers' mean reserve is 0.90–0.91.
- In seed d, caregivers nursed up to 5 dependents at once, on 70 days.

## Milk (whole run)

| Seed | Supply cap (kcal/nursing day) | Produced = charged = absorbed | Unabsorbed | Demand-limited days | Child store clamp (kcal/nursing day) |
|---|---|---|---|---|---|
| a | 294.0 | 141.3 | 0 | 96% | 28.5 |
| b | 294.6 | 149.1 | 0 | 92% | 24.4 |
| c | 273.7 | 135.6 | 0 | 88% | 29.3 |
| d | 288.8 | 143.5 | 0 | 92% | 26.1 |

The child store clamp is the remaining erasure. It is not milk: children aged 2–5 feed themselves above their size-scaled store, and on a nursing day they are cut back to it. It is zero in years 1–2 and grows as children reach 2:
- seed a: 36,383 kcal in year 3, 131,616 in year 4 and 189,744 in year 5;
- seed d: 169,225 kcal in year 5.

This is the pre-existing defect flagged in `CAREGIVING_SOLID_FOOD.md`; the milk accounting now makes it visible.

## Hand-feeding checks, grouped by caregiver reserve

Each cell gives the number of checks, then the share of children past 180 days at or above the 0.75 trigger.

| Seed | All checks | Fed | Caregiver reserve < 0.25 | Caregiver reserve < 0.75 | Caregiver reserve ≥ 0.75 |
|---|---|---|---|---|---|
| a | 12566 | 32 | 28; 17 of 17 at or above | 931; 100% | 11607; 99.7% |
| b | 10183 | 23 | — | 194; 97.6% | 9989; 99.7% |
| c | 5039 | 6 | — | 155; 98.7% | 4884; 99.6% |
| d | 12473 | 21 | 27 (all too young) | 272; 98.2% | 12174; 99.8% |

- There were 82 hand-feedings across the four seeds.
- Children past 180 days stay at a median reserve of 1.0, whatever their caregiver's reserve.
- This is consistent with the hypothesis that milk keeps children above the trigger while caregivers run down. This audit does not separate milk from the child's own eating (children over 2 forage), so the hypothesis is supported, not established.

## Adults' intake beyond need

Kg eaten per day, and how much of it was eaten beyond need (its energy refused by a full reserve):

| Group | Seed a | Seed b | Seed c | Seed d |
|---|---|---|---|---|
| Non-caregivers | 1.325, 0.245 beyond need | 1.325, 0.348 | 1.338, 0.367 | 1.327, 0.354 |
| Caregivers | 1.317, 0.335 | 1.311, 0.243 | 1.301, 0.239 | 1.317, 0.228 |

Roughly a fifth to a quarter of adult intake is eaten beyond need. That plant mass leaves the world unused. It is small next to plant flows: Agentus remove 2.6–3.4 t of edible plant a year, against 200–1,400 t of growth.

## Animals (year-end counts)

| Seed | Year 1 | Year 5 |
|---|---|---|
| a | browser 2, grazer 1, stalker 1 | grazer 4 |
| b | browser 2, grazer 1 | browser 1, grazer 4 |
| c | browser 2, grazer 1, stalker 1 | browser 3, grazer 4 |
| d | browser 2, stalker 1 | browser 3 |

- Seed d has had no grazers since year 1: Agentus killed 2 in year 1.
- The stalker is gone in every seed by year 2.
- Animals remove 0.1–0.3 kg of edible plant a year.

## Learned behaviour

- Imitation: 15 tries across the four seeds, none paid off. Following: 0.
- Positive learned values include striking animals with stones and stripping bark with stones. No object is worn and no object use is traced to a benefit.

## Plants

Year-end edible mass (t), inhabited worlds and their plant-only controls:

| Seed | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Year 10 |
|---|---|---|---|---|---|---|
| a, inhabited | 45.1 | 17.4 | 7.1 | 5.0 | 1.86 | — |
| a, control | 85.6 | 15.1 | 6.7 | 3.0 | 1.83 | 0.86 |
| b, inhabited | 47.9 | 19.7 | 6.8 | 3.9 | 1.51 | — |
| b, control | — | — | — | — | — | 0.88 |
| c, inhabited | 59.3 | 16.1 | 7.6 | 3.9 | 1.52 | — |
| c, control | — | — | — | — | 1.57 | 0.86 |
| d, inhabited | 50.2 | 19.7 | 7.0 | 4.6 | 1.69 | — |
| d, control | — | — | — | — | 1.63 | 0.87 |

Yearly peak edible mass in the controls (t):

| Seed | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Year 6 | Year 7 | Year 8 | Year 9 | Year 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| a | 133 | 172 | 89 | 74 | 54 | 42 | 15.5 | 10.4 | 7.7 | 6.1 |
| c | 172 | 157 | 114 | 79 | 47 | 44 | 25 | 12.6 | 9.1 | 6.5 |
| d | 141 | 168 | 96 | 70 | 50 | 39 | 22 | 14.5 | 10.5 | 7.4 |

Annual edible growth in control a fell from 1,323 t in year 2 to 40 t in year 10.

Readings:
1. **The decline is intrinsic to the plant system.** By year 5 the inhabited and control worlds hold the same edible mass to within about 5%. Consumers make no measurable difference to the stock by then.
2. **The decline has not stopped.** Year-end values level off near 0.86–0.88 t only because year end is the seasonal low. Yearly peaks still fall about 20–30% a year at year 10.
3. **Cause not yet established.** Every flow is accounted for. What limits growth year after year (conditions, soil elements, or live mass carrying over the low season) has not yet been measured.

## Follow-up: what limits plant growth (read-only, control seed a, 10 years, local run)

| Year | Mean condition min(light, temp, water) | Growth realized / desired | Soil elements (t) | Soil water (t) | Live mass at year end (t) | Cells with plants |
|---|---|---|---|---|---|---|
| 1 | 0.642 | 0.999 | 21,753 | 9,523 | 101.4 | 223 |
| 2 | 0.477 | 0.960 | 21,828 | 4,763 | 19.5 | 231 |
| 3 | 0.347 | 0.977 | 21,948 | 3,306 | 8.8 | 256 |
| 4 | 0.409 | 0.984 | 22,005 | 2,306 | 4.3 | 256 |
| 5 | 0.487 | 0.999 | 22,024 | 1,591 | 3.0 | 256 |
| 6 | 0.513 | 0.987 | 22,041 | 1,055 | 1.8 | 256 |
| 7 | 0.511 | 0.998 | 22,058 | 865 | 1.15 | 256 |
| 8 | 0.529 | 1.000 | 22,062 | 759 | 1.11 | 256 |
| 9 | 0.537 | 1.000 | 22,064 | 693 | 1.09 | 256 |
| 10 | 0.540 | 1.000 | 22,065 | 648 | 1.03 | 256 |

- **Not soil elements.** Growth gets 96–100% of what it asks for, and soil elements rise slightly.
- **Not water, by the model's own rule.** Soil water falls 93%, but at year 10 it is still about 2.5 t per cell. The water factor saturates at 18 kg per cell, so water does not lower the condition.
- **Not loss of ground.** Every cell carries some vegetation from year 3.

**Leading hypothesis (inferred from the stated constants, not yet measured per cell-day):**
- Daily rates are: growth 0.055 × condition; mortality 0.004 + 0.08 × (1 − condition); reproduction 0.012 whenever condition ≥ 0.5.
- Net daily change is therefore positive only above a condition of about 0.62 (about 0.71 on days when reproduction applies).
- Year 1 averaged 0.64. Years 2–10 averaged 0.35–0.54, so live mass shrinks geometrically, buffered by the seed bank.
- The plant gate (`run_g2_gate.py`) validates plants at 24 ticks/year for 10 years. No gate covers multi-year plant persistence in the 365-day world.

**Not yet established:** why year 1's conditions differ from later years (weather drift, or initial state), and whether the break-even arithmetic holds cell by cell. Both can be measured without changing growth.

---

# Third run: water cycle at material scale (Railway, build 83ba80b, 2026-10-08/09)

## Setup

- Same configuration as the second run, plus `water_cycle_scale = "material-v1"`.
- Each ledger is valid. All four seeds completed 5 years.
- World report and plant ledger: deployment `03e9b68a`.
- The caregiver audit runs separately on the same build (deployment `8ed5e891`).

## Families (previous run in brackets)

| Seed | Births | Survived to 1 year | Survived to 2 years | Deaths | Alive at end of year 5 | Dependents at end of year 5 |
|---|---|---|---|---|---|---|
| a | 8 (11) | 7/7 | 6/6 | 0 (0) | 16 (19) | 8 |
| b | 11 (9) | 9/9 | 7/7 | 0 (0) | 19 (17) | 11 |
| c | 5 (4) | 4/4 | 3/3 | 0 (0) | 13 (12) | 5 |
| d | 20 (11) | 16/16 | 12/12 | 0 (0) | 28 (19) | 20 |

- Adults are still the 8 founders; no child has had children yet.
- Seed d had 4 births in every one of the 5 years, so 8 adults now care for 20 dependents.

## Hand-feeding

- 0 hand-feedings in any seed (82 in the previous run).
- Every check of a child past 180 days found the child not hungry.

## Milk and the child energy clamp

- Milk produced, charged and absorbed are equal; nothing is unabsorbed.
- The child energy clamp, a separate open defect, is larger than before. Seed d alone erased 319,867 kcal in year 5.

## Animals

| Seed | End of year 5 (previous run) | Grazers | Stalker |
|---|---|---|---|
| a | 3 browsers (4 grazers) | All killed by Agentus: 2 in year 1, 1 in year 2 | Died of starvation in year 3 |
| b | 5 browsers, 4 grazers (1 browser, 4 grazers) | Survive | — |
| c | 6 browsers, 2 grazers, 1 stalker (3 browsers, 4 grazers) | Survive | Survives, and killed one animal itself in year 2 |
| d | 5 browsers (3 browsers) | Killed by Agentus in year 1, as in the previous run | Died of starvation in year 2 |

- **Successful hunts:** 8 in total (a 3, b 2, c 1, d 2), all in years 1–3. The previous run had 15, spread through year 5.

## Learned behaviour

- **Imitation:** 34 tries, none paid off (previous run: 15, none paid off).
- **Following:** 0 days in every seed, in both runs.
- **Acts with positive learned value:**
  - Striking a grazer with a stone (seeds a and d), learned from the captures in years 1–2.
  - A few fibre and stone acts.
- **Repeated acts:** almost all in year 1. The previous run had more repeated stone and fibre acts in years 4–5.
- **Objects:** 219–279 made. None worn.

## Plants (year-end edible mass, inhabited)

| Seed | Year 1 | Year 2 | Year 3 | Year 4 | Year 5 | Year 5, previous run |
|---|---|---|---|---|---|---|
| a | 47.8 t | 566.5 t | 698.6 t | 768.5 t | 771.3 t | 1.86 t |
| b | 49.1 t | 599.6 t | 702.8 t | 748.0 t | 772.6 t | 1.51 t |
| c | 69.2 t | 608.0 t | 721.6 t | 759.1 t | 789.4 t | 1.52 t |
| d | 51.5 t | 594.1 t | 702.5 t | 758.3 t | 777.6 t | 1.69 t |

These track the corrected plant-only control (771 t at year 5 for seed a).

## Readings, not repairs

- **Vegetation recovered; family outcomes did not move together.** Births fell in seed a and rose sharply in seed d. No one died in either run.
- **Hunting fell and hand-feeding stopped.** Both are consistent with the larger food supply lowering the need to hunt or to hand-feed. That is recorded as a result, not tuned.
- **Grazer extinctions in a and d are caused by Agentus hunting in years 1–2.** The stalker deaths in those two seeds follow them, recorded as starvation.

**Reproducibility check.** A redeploy of build 83ba80b (`8ed5e891`) reused its stored start command by mistake and re-ran the seed a world report. The result was identical: 16 alive, 8 births, 0 deaths, the same animals by year (grazers killed by Agentus in years 1–2, the stalker starved in year 3), and 771.3 t of edible plants at year 5. The caregiver audit runs from a fresh deployment of the same code. The commits since 83ba80b change documentation only.
