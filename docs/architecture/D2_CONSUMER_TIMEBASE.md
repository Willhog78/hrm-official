# D2 — Consumer timebase correction (animal units)

**Status:** implemented as a versioned baseline correction, authorized by the owner on 2026-10-07 (decision D2, first part).
- Flag: `consumer_timebase`. `"elapsed-time-v1"` is the default; `"per-tick-legacy"` reproduces earlier runs exactly.
- Life-history **recalibration** (D2, second part) is **not** part of this change and remains open.

## 1. What was wrong, in plain terms

Animal traits are written for a world that ticks once a month: "a grazer matures at 28 months, burns 0.2 energy a month, loses 0.009 kg of water a month". The simulation can tick at any rate, and the Agentus world ticks daily (365 times a year).

Before this change, the code converted only half of those numbers:
- **Durations were converted.** At daily ticks, "28 months" correctly became 852 days.
- **Rates were not converted.** "0.2 energy a month" was charged every tick. At daily ticks an animal therefore paid a month's metabolism, lost a month's water and took a month's bite of food **every day**, about 30× too much per year. Carcasses also decayed a month's worth every day.

So in the Agentus world, animals lived on a monthly calendar but ate and starved on a daily one. Concretely:
- herbivores ate so fast that they sat at their energy ceiling;
- the predator, which cannot graze, starved within its first weeks. That is G10.4's "the predator starves in year 1".

## 2. What changed

Under `elapsed-time-v1`, every quantity stated *per month* is converted to the run's tick length, exactly as durations already were:

| Quantity | Kind | Conversion |
|---|---|---|
| basal energy cost (`basal_cost`) | flow per month | × (12 / ticks per year) |
| water loss (`water_loss_per_tick_kg`) | flow per month | × (12 / ticks per year) |
| bite cap (0.004 kg) | flow per month | × (12 / ticks per year) |
| bite fraction (`bite_fraction`) | fraction of the plant stock per month | compounded: 1 − (1 − f)^(12 / ticks per year) |
| carcass decomposition (5%) and carcass water return (10%) | fraction per month | compounded, as above |
| minimum supported streak before breeding (5) | count of months | scaled like durations |

The reproduction support requirement (basal cost per tick × breeding-interval ticks) needed no edit. Once basal cost is per tick, the product is the same at any timebase.

**Not converted, deliberately** (code comment "TIMEBASE note" in `ecology/animals.py`):
- **Per-event costs:** movement energy per cell moved, the cost of a failed hunt, an escape.
- **Per-event learning steps:** `forage_bias`.
- **Hunt success per attempt.**
- **Movement speed:** one cell per tick at any timebase. Animals therefore still cover about 30× more ground per month at daily ticks, and attempt hunts daily rather than monthly. Normalizing speed would need fractional movement. That is a behaviour change, not a unit conversion, and it is recorded as a remaining difference.
- **Agentus physiology,** including predator injury to Agentus per tick. That is the human model's own calibration.

**Where the code is.**
- Conversions: `ecology/traits.py` (`per_tick_amount`, `per_tick_fraction`, `scaled_ticks`).
- Uses: `ecology/animals.py`.
- Flag: `config.py`. It is recorded in the fingerprint and the consumer state only where it changes behaviour (consumers on, not 12 ticks/year). Older states without the key replay as legacy.

## 3. What did not change (verified)

Ledger digests and fingerprints for fixed configurations were compared before and after the change (`experiments/genesis/check_consumer_timebase_digests.py`):

| Configuration | Default (`elapsed-time-v1`) | `per-tick-legacy` |
|---|---|---|
| ecology at 12 ticks/year, 30 years | **identical** digest and fingerprint | identical |
| ecology at 24, 36 and 365 ticks/year | changed (as intended) | **identical** |
| Agentus `v1`, 60 days | changed (as intended) | **identical** |

- Monthly-tick worlds, including the G4 century run, are bit-identical.
- Every earlier result can be reproduced with `consumer_timebase="per-tick-legacy"`.

## 4. Validation

**Equivalence tests** (`tests/genesis/test_consumer_timebase.py`, 9 tests). Each places one grazer in fixed conditions and compares one simulated year at 12 and at 365 ticks/year:
- basal energy and water loss agree (relative error ≤ 1e-6). Under legacy, the same grazer dies of dehydration within the year: its water lasts about 34 days.
- plant removed agrees (relative error ≤ 1e-5), both when the stock limits the bite (fraction regime) and when the cap does. Under legacy, the grazer strips a small patch, and in the cap regime it eats 365/12 times as much.
- carcass mass remaining after a year agrees (0.95¹² of the start). Under legacy, the carcass is effectively gone.
- whole-world element and water balance holds at daily ticks.
- monthly and legacy fingerprints are unchanged, and unknown timebase names are rejected.

**Population-level comparison** (`experiments/genesis/run_consumer_timebase_comparison.py`): the Agentus world's ecology without Agentus (16×16, material scale 1000), 3 seeds × 5 years. Exact trajectories are not expected to match, because weather, plants and movement are per tick. Per-year quantities:

| | monthly (12/yr) | daily, legacy | daily, elapsed-time |
|---|---|---|---|
| element / water balance error | ≤ 6e-16 / ≤ 3e-16 | ≤ 3e-14 / ≤ 9e-13 | ≤ 2e-14 / ≤ 8e-13 |
| predator survives (years; seeds a / b / c) | ≈3.2 / ≈2.3 / ≥5 | 0.1 / 0.1 / 1.2 | 4.4 / 1.1 / 1.7 |
| mean herbivore energy (ceiling 52–60) | 34–55 | 54–60 | 29–57 |
| births over 5 years | 25 | 22 | 22 |

The correction moves daily-tick ecology toward monthly-tick behaviour:
- the predator lives for years instead of weeks;
- herbivores are no longer pinned at their energy ceiling.

It does **not** change herbivore reproduction. Births are about the same in all three arms, because breeding is limited by the 28-month maturity and the 30-month interval, which were already converted. G10.4's finding that "life history is the bottleneck" therefore stands, and it is a calibration question, not a units question.

**Regression suite and gates.**
- All 19 gate scripts pass.
- Micro tier passes. Smoke tier: 0 fail, 0 warn.
- `tests/genesis`: one test changed. `test_g3_no_food_causes_consumer_collapse` encoded collapse horizons in ticks (100 and 300) that only held under per-tick rates. It now states them in simulated years:
  - herbivores gone within 5 years;
  - the predator's energy never rises once prey and plants are gone;
  - everything gone within 15 years.

  Measured: herbivores at 4.2 years, all gone at 13.3 years. Under legacy and 120 ticks/year these were 52 and 159 ticks, i.e. 0.4 and 1.3 years.

## 5. What it changes for Agentus

The Agentus world runs at 365 ticks/year, so every Agentus run's fingerprint changes. Observed effects:
- **Predators persist and bite.** On smoke seed `agentus-g10-4-01` (75 days):
  - the stalker now lives all 75 days, where under legacy it died by day 20;
  - attacks on Agentus rise from 11 to 25, and one agent dies of injury.

  Predators injure Agentus but cannot eat them (decision D1, open). That limitation is now active rather than moot.
- **Smoke tier** (3 seeds × 75 days): 0 fail, 0 warn. Before → after:
  - alive 9/8/9 → 8/8/8;
  - births 1/0/1 → 0/0/1;
  - kills 2/0/1 → 2/0/1;
  - one injury death.
- **Two-year opportunity census** under the corrected default: section 6.
- **Cause of injury deaths (added 2026-10-08).** The budget audit (`qualification/genesis/budget_audit.py`) records injury gain by source. All 7 injury deaths in the two-year `v1` audit are 98–100% from the unprovoked predator bite: 5 children after about 4 bites each, and 2 adults after 21–22 bites in 60 days. The attribution in section 6 is now supported by cause tracking, not only by inference.

## 6. Two-year census under the corrected default

Arm `v1`, 4 seeds × 730 days (`experiments/genesis/summaries/opportunity_census_v1_elapsed-timebase_2026-10-07.json`), compared with the census in `ECOLOGY_OPPORTUNITY_OPENING.md`, which ran on the earlier timebase:

| | before (per-tick) | after (elapsed-time) |
|---|---|---|
| agents alive at end (sum of 4 seeds) | 51 | 42 |
| births | 21 | 17 |
| injury deaths | 2 | **7** |
| starvation or dehydration deaths | 0 | 0 |
| full day's food in view | 99.6% | 99.7% |
| hungry: all / year 2 | 6.5% / 0% | 6.7% / 0% |
| follow opportunity (hungry, nothing known, peer in view) | 0 | 0 |
| useful non-meal acts performed (with an audience) | 792 (41%) | 763 (35%) |
| imitated tries (paid) | 18 (0) | 11 (0) |

- **The opportunity conclusions of the ecology opening are unchanged.** Food is abundant and in view, following has no opportunity, and useful acts are rare at the source.
- **What changes is mortality.** Injury deaths rise from 2 to 7, which lowers survivors and births. Predators now survive and bite Agentus, and on one smoke seed the extra injury death was attributed to predator attacks (section 5). The census itself does not attribute injury causes. The later budget audit does: all 7 are predator bites (section 5).
- This makes decision D1 (whether predators can eat what they kill or injure) a live question rather than a moot one.

## 7. What this exposes (not fixed here)

With rates honest, the trait values themselves become visible:
- **Starvation endurance:** a starving 50 g grazer lasts about 4 years; a predator with a full store about 13.
- **Life-history scale:** maturity at 28 months, one young every 30 months, a 27-year lifespan. That is a large mammal's life history on a 50 g body.

These values were tuned for persistence at monthly ticks and carry no body-size reference. Correcting them is D2's second part (allometric recalibration), which needs its own authorization and re-qualification of G3/G4.

## 8. Encounter frequency: rates are equivalent, ecology is not

The equivalence tests show that a simulated year *costs* the same at any timebase. They do not show that the ecology is equivalent. Movement is one cell per tick, and hunt success is rolled per attempt, so a daily-tick world offers far more movement and more encounters per simulated year. Measured in `run_consumer_timebase_comparison.py` (3 seeds × 5 years, ecology without Agentus):

| per simulated year | monthly (12/yr) | daily, legacy | daily, elapsed-time |
|---|---|---|---|
| cells travelled per browser / grazer / stalker | 0.2 / 0.1 / 1.1 | 15.7 / 5.9 / 27.3 | 15.6 / 5.9 / 29.1 |
| predator hunt attempts per predator-year | 0.1 | 5.2 | 1.4 |
| predator-years lived (sum) | 10.5 | 1.4 | 7.2 |

**Consequences:**
- At daily ticks, animals travel 25–80× farther per year, and the predator makes about 14× more hunt attempts per predator-year than at monthly ticks.
- Predator persistence at daily ticks (section 4) is therefore not evidence of ecological equivalence with the monthly world. It is the corrected cost budget combined with a much higher encounter rate.
- Predator attacks on Agentus are counted by the budget audit, by year, before predator mortality or Agentus injury deaths are interpreted:
  - `v1`: 110 attacks in year 1 and 101 in year 2, summed over 4 seeds;
  - `reference-v2`: 67 and 158.

**Not changed here.** Making movement and encounter frequency timebase-independent needs fractional movement, or a per-time encounter rate. Either is a behaviour change, not a unit conversion, and needs its own decision.

## 9. Elapsed-time opportunities (`elapsed-time-v2`, 2026-10-08)

**Status:** implemented, and the new default. `elapsed-time-v1` (section 2, rates only) and `per-tick-legacy` remain selectable and reproduce their runs exactly.

### Rule

Each animal has **one movement opportunity, one hunt opportunity and one attack opportunity (on a co-located agent) per reference tick of elapsed time** (one month, as at 12 ticks/year).
- At other tick lengths each opportunity is a deterministic per-tick draw with probability 12 / ticks per year (`traits.has_opportunity`).
- The expected number per simulated year therefore matches the reference timebase. The process has a constant rate, like a Poisson process, rather than regular spacing.
- The animal still chooses where it would go every tick. It moves only on a tick with a movement opportunity.
- At 12 ticks/year the probability is 1, so no draw is made and nothing changes. Below 12 ticks/year it is capped at one per tick.

What is not changed:
- per-event costs;
- escapes caused by Agentus;
- Agentus movement, which is calibrated per day;
- animal speed itself (one cell per reference month). That belongs with the life-history recalibration.

### Unchanged runs (verified by ledger digest and fingerprint, `check_consumer_timebase_digests.py`)

| | 12 ticks/yr | 24, 36, 365 ticks/yr and Agentus `v1` 60 days |
|---|---|---|
| `per-tick-legacy` vs pre-D2 commit | identical | identical |
| `elapsed-time-v1` vs D2 commit | identical | identical |
| `elapsed-time-v2` (default) | identical | changed (as intended) |

### Opportunities in fixed conditions (`tests/genesis/test_consumer_opportunity.py`, 6 tests)

| | monthly | daily, `v2` | daily, `v1` |
|---|---|---|---|
| cells moved in 5 years by a grazer that always wants to move | 60 | 56 | 89 (stopped at the strip's end; about 1,825 uncapped) |
| hunt attempts in 1 year, hungry predator beside prey it never catches | 12 | 10 | 46 (until it starved from failed-hunt costs) |
| attacks in 1 year, hungry predator in an agent's cell | 12 | 3–25 (test range) | 365 |

The opportunity *rate* is now timebase-independent.

### Population level: residual difference, measured

Ecology without Agentus, 3 seeds × 5 years (`run_consumer_timebase_comparison.py`):

| per simulated year | monthly | daily, legacy | daily, `v1` | daily, `v2` |
|---|---|---|---|---|
| cells travelled per browser / grazer / stalker | 0.2 / 0.1 / 1.1 | 15.7 / 5.9 / 27.3 | 15.6 / 5.9 / 29.1 | **5.2 / 1.6 / 7.3** |
| hunt attempts per predator-year | 0.1 | 5.2 | 1.4 | **0.8** |
| predator-years lived (sum) | 10.5 | 1.4 | 7.2 | 15.0 |
| deaths (5 years) | starvation 2, predation 1 | starvation 3, predation 2 | starvation 3, predation 2 | predation 3 |
| element / water balance | holds | holds | holds | holds |

`v2` cuts daily movement 3–4× and hunt attempts about 2×, but **daily animals still move 8–26× more than monthly ones**. The cause, as far as it has been traced:
- **More episodes, not more opportunities.** The excess comes from far more *episodes of wanting to move* per simulated year (an episode starts when the animal wants to leave its cell after not wanting to):
  - monthly: 0.4–0.6 per year;
  - daily `v2`: 8–15.5;
  - daily `v1`: 53.5.

  `v2` limits moves to about 12 per year, but each episode is eventually acted on.
- **What starts episodes** (daily `v2`, seed a, 2 years): mostly the animal's own cell falling below a neighbour's (10 per year), then water or distance (3.5), then a neighbour rising (2).
- **Sizes at onset** (1 year, seeds a and b): the animal stands on a median 119–262 kg of plant tissue, and the better neighbour holds a median of about 94 kg more. A grazer can eat at most 0.004 kg per month.

So the destination rule responds to differences in standing biomass that are irrelevant to what the animal can eat.

**Producer timebase, checked in code (2026-10-08).** The plant model applies its rates per tick with no timebase conversion (`ecology/plants.py`):
- `BASE_GROWTH_FRACTION` 0.055;
- `BASE_MORTALITY_FRACTION` 0.004;
- `DECOMPOSITION_FRACTION` 0.035;
- `SEED_GERMINATION_FRACTION` 0.0165;
- `REPRODUCTION_FRACTION` 0.012;
- `MAX_AGE_TICKS` 360.

The plant-lifecycle corrections reason in days ("95% of a seed cohort germinates within about 180 viable days"), so plants appear to be tuned per day (**inferred**), while animal traits are stated per month.

A 12-ticks/year world therefore runs a different plant ecology from a 365-ticks/year world: plants grow and die about 30× less per simulated year. **The monthly-versus-daily animal comparisons above are not like-for-like.** Part or all of the residual movement difference may come from plant fields that differ between the two worlds, not from animal behaviour. This is not yet separated.

**Effect on Agentus** (two-year audit and census, `v1`, 4 seeds, default `elapsed-time-v2`; `budget_audit_v1_timebase-v2_2026-10-08.json`):

| | D2 (`elapsed-time-v1`) | `elapsed-time-v2` |
|---|---|---|
| predator attacks on Agentus, year 1 / year 2 (sum of 4 seeds) | 110 / 101 | 2 / 3 |
| injury deaths | 7 | 0 |
| agents alive at end / births | 42 / 17 | 53 / 21 |
| imitated tries (paid) | 11 (0) | 14 (0) |
| useful non-meal acts (with an audience) | 763 (35%) | 793 (40%) |

Every opportunity conclusion of the ecology opening still holds.

With opportunities equalized, predators now rarely meet agents. That is **not** a calibrated predation rate: animal speed (one cell per month) and the plant timebase are both still uncalibrated. It does mean the unprovoked-bite deaths of D2 were mostly an artefact of daily encounter frequency.

**Decision needed before predator calibration (proposed, not implemented):**
- **(a)** Score destinations by what the animal can actually eat there (food up to its per-tick bite) and by water need, not by standing mass. That is a behaviour change with a physical justification. It would also change monthly behaviour and require G3/G4 re-qualification.
- **(b)** Audit the producer timebase first: are plant rates per tick converted, as consumer rates now are?

Recommendation: (b), then (a). (b) now has a concrete target: give producers a stated reference timebase and convert their per-tick rates, as D2 did for consumers. Only then is a monthly-versus-daily comparison of animal behaviour like-for-like.
