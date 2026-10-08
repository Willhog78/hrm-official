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
