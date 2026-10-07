# Ecology opening — why social learning has no opportunity

**Timebase note (D2).** The census results in sections 4–5 ran before the consumer timebase correction (`docs/architecture/D2_CONSUMER_TIMEBASE.md`). That correction lets predators survive at daily ticks. Re-running the `v1` census under the corrected default leaves every opportunity conclusion unchanged. It raises injury deaths from 2 to 7, inferred to be mostly predator bites (D2 note, section 6).

**Status:** design opening. Step 1 (measurement) is done. Step 2 (controlled experiments) is proposed here and **not implemented**. Owner decisions are listed in section 7.

**Owner decision (2026-10-07).** Cognition work is paused until this question is answered: which condition keeps social learning from having an opportunity? The candidates are measured separately and together:
- hunger;
- no reachable known food;
- another agent nearby;
- a useful act witnessed.

**Rule.** Animal reproduction is not raised, and agents are not crowded together, merely to make cognition produce a result. Every world change proposed here carries a biological or environmental justification, stated before its result is known. Otherwise the model would be furnishing the demonstration it was meant to discover.

**Milestone.** An explanation of the missing opportunities, even if the explanation is that following and imitation have little value in this world.

## 1. Answer in brief

In the current world (`v1`, 4 seeds × 730 days), the four conditions behave very differently.

| Condition | How often (independent agent-days) | Binding? |
|---|---|---|
| Hunger (planner's own test) | 6.5% overall; 50% in year 1 Q1, **0%** in year 2 | Founding transient only |
| No reachable known food | 0.1% (14 days, all in year 1 Q1) | Yes, for following: almost never true |
| Another individual in view | 64%; non-kin 43% (10% in year 1 Q1) | No, except in the founding months |
| Useful non-meal act witnessed | 0.8% | Yes, for imitation: useful acts are rare at the source |

- **Following** is consulted only when an agent is hungry and knows no food. That situation occurred on 14 agent-days in two years, all in the founding quarter, and never with anyone in view. Food is not scarce in this world. A full day's food was in view on 99.6% of agent-days. No day in two years had zero cells holding one adult-day of plant tissue. There were no starvation deaths. Following has no opportunity because food is everywhere in view, not because of perception or co-presence.
- **Imitation** needs a useful act performed where someone can see it. Co-presence is common after founding: a non-kin agent shared the cell on 26% of agent-days. But useful non-meal acts are rare: 792 in 23,360 agent-days (3.4%). Of these, 41% had an audience. Of the 18 imitated tries, none paid. The limit is that useful acts are rarely performed and copying them does not pay. Absence of an audience is not the limit.
- **Founding layout** does suppress contact, but only at first. Eight founders are placed as four pairs, one pair per 8×8 quadrant, each founder on a different cell. Witnessing needs a shared cell. In year 1 Q1, a non-kin agent is in view on 9.9% of agent-days and in the same cell on 3.1%. Once births create caregiving groups and agents move, co-presence rises well above any other limiting condition.

**Conclusion.** In this world, following and imitation have little to act on. Food is abundant and visible, and the transmissible acts are rare and do not pay. Neither perception range nor co-presence is the binding limit after the founding months. An ecological change aimed at social learning is justified only if it is justified on its own terms, and the census tells us which kind would matter:
- for following: spatial or seasonal food scarcity;
- for imitation: acts whose payoff is real.

Density would matter for neither.

## 2. Corrections to earlier statements

- **"Hungry 94% of the time"** came from a 40-day run. That is entirely the founding transient: `reference-v1` founders start near a reserve of 0.67. Over two years the figure is 6.5%, and 0% in year 2.
- **Second-winter shortage.** `AGENTUS_FOOD_INTAKE_DIAGNOSIS_2026-10-07.md` found real shortage on days 355–439: a map-wide minimum of 12–27 kg, and in half the deaths no cell held a day's food. That does not reproduce in the current model.
  - The year-2 minimum is 15.5 t (`v1`) and 14.4 t (`reference-v2`).
  - At least 91 of 256 cells held one adult-day (1.14 kg) on every day.

  The likely cause is the plant-lifecycle corrections (`AGENTUS_PLANT_LIFECYCLE_CORRECTIONS_2026-10-07.md`, "a winter trough of tens of tonnes"). That is **inferred**; this census only shows the shortage is absent.
- **"The world is food-rich" is true now, not generally.** Winter remains the trough: year-1 Q1 plant tissue is 2.6 t mean and 0.9 t minimum map-wide. It is still enough for about 8 agents.

## 3. Method

`qualification/genesis/opportunity.py` (read-only):
- It wraps `biology.choose_destination`, `interactions.remember_witnessed` and `interactions.observe_outcome` to look at their inputs. Each wrapper returns exactly what the original returned.
- **Non-causal.** With and without the census, the ledger digest is identical on all four seeds over 730 days (`--check-digest`, first run). `tests/genesis/test_opportunity_census.py` checks the same on a short run.

What is classified, and from what:
- **Planner's view.** Hunger, the thirst override and known food are classified from the perception the planner receives, in the planner's own order: full day in view → full day remembered → partial above the giving-up level → none.
- **Peers.** Peers are the visible individuals in perception: own cell plus the 4 neighbours.
- **Kin.** Kin means caregiver lineage: caregiver, dependent, or the same caregiver.
- **Witnessed useful.** An event counts as useful when `witnessed_salience > 0`, i.e. at least one visible consequence.
- **Useful acts performed.** These are counted at the actor, with whether anyone (and any non-kin) shared the cell.

Run details:
- **Seeds and arms.** Seeds `agentus-demography-a..d`; arm `v1` (production: capacities, thirst, G10.6 integrity, G10.7a on), and `v1@reference-v2`.
- **Duration and breakdown.** 730 days, reported by year and by quarter of year (year-days 0–90, 91–181, 182–272, 273–364).
- **Data.** `experiments/genesis/summaries/opportunity_census_v1_2026-10-07.json` and `…_v1_reference-v2_2026-10-07.json`.

## 4. Results

### 4.1 Conditions, separately (% of independent agent-days)

| | v1 | reference-v2 |
|---|---|---|
| agent-days | 23,360 | 23,360 |
| hungry (reserve < 0.75) | 6.5% | 2.3% |
| thirst decided the move | 2.5% | 2.4% |
| full day's food in view | 99.6% | 99.6% |
| full day remembered (not in view) | 0.3% | 0.4% |
| partial food only | 0.04% | 0.02% |
| no food known | 0.06% | 0.01% |
| anyone in view / in own cell | 63.7% / 55.9% | 65.8% / 57.2% |
| non-kin in view / in own cell | 42.8% / 25.7% | 50.8% / 32.5% |
| witnessed a useful act (non-meal) | 0.8% | 1.1% |

By period (v1):

| | year 1 Q1 | year 1 Q2–Q4 | year 2 |
|---|---|---|---|
| hungry | 50.1% | 0–2.3% | 0% |
| mean reserve | 0.67 | 0.92–0.93 | 0.93 |
| non-kin in view | 9.9% | 35–43% | 54.7% |
| non-kin in own cell | 3.1% | 13–27% | 36.2% |
| map-wide plant tissue, mean (min) | 2.6 t (0.9 t) | 2.8–69 t | 102 t (15.6 t) |

### 4.2 Conjunctions (v1, agent-days)

- Hungry and no full day known: 23 (14 none, 9 partial), all in year 1 Q1.
- Hungry and someone in view: 206, almost all in year 1 Q1.
- **Follow opportunity** (hungry, thirst not deciding, no food known, someone in view): **0**.
- Follow opportunity if the partial-food anchor did not come first: 0.
- Follow branch reached: 14. Followed: 0.
- Overlap (hungry, no known full food, peer in view, witnessed useful):
  - only peer in view: 62.0%;
  - none of the four: 30.7%;
  - hungry alone: 5.5%;
  - hungry and peer in view: 0.9%;
  - peer in view and witnessed useful: 0.8%;
  - every other combination: ≤ 0.1%.

  The pattern that following needs (hungry, nothing known, peer in view) does not occur.

### 4.3 Useful acts at the source

| | v1 | reference-v2 |
|---|---|---|
| useful non-meal acts performed | 792 | 794 |
| … with anyone in the cell | 41.0% | 49.7% |
| … with a non-kin in the cell | 20.6% | 29.0% |
| imitated tries (paid) | 18 (0) | 46 (0) |
| dependent-days that witnessed a useful act | 253 of 9,248 | 309 of 9,007 |

### 4.4 Outcomes

Over 2 years, the 4 seeds end with 12–14 agents each under `v1` and 11–14 under `reference-v2`, and births are 21 (`v1`) and 19 (`reference-v2`). There were no starvation or dehydration deaths. `v1` had 2 injury deaths.

## 5. What the hunger label means under each physiology

The planner calls an agent hungry when energy / satiety reference < 0.75. The same label describes different physical states.

- **reference-v1.** Hunger is a founding transient. Founders start at a reserve of about 0.67, and hunger clears by the end of year 1 Q2 as they eat from abundant visible food. After that, mean reserve is 0.93 with nothing below 0.75. The label then means *recovering from a low starting reserve with food in view*.
- **reference-v2.** Founders start full (reserve 1.00). Hunger appears in year 2 Q3–Q4 on 4.4% of year-2 agent-days, and it is deep: 400 of 544 hungry days are below 0.25. A full day's food was in view on every one of those days, and there were no starvation deaths. The label then means *a sharp reserve drop with food in view*. That points to a demand or intake limit rather than food access. Section 5.1 shows that every one of these days belongs to a caregiver.

Consequence. A "hungry" rate cannot be compared across physiologies, or used as a scarcity measure, without the reserve level and intake behind it. Any experiment below reports the reserve bins, not the label alone.

### 5.1 Caregiving check (reference-v2)

The census marks an agent as *caring* on days when it is the caregiver of a living dependent. The reference-v2 rerun is deterministic, and every other number matches the run in section 4.

| reference-v2, 4 seeds × 730 days | agent-days | of which caring |
|---|---|---|
| all independent agent-days | 23,360 | 8,080 (34.6%) |
| hungry (reserve < 0.75) | 544 | **544 (100%)** |
| reserve < 0.25 | 400 | **400 (100%)** |

- Under reference-v2, every hungry agent-day, deep or not, belongs to a caregiver.
- A full day's food was in view on all of them, and none ended in starvation.

The reference-v2 hunger signal is therefore the **cost of caregiving**, not scarcity.

**Contrast with reference-v1.** Under v1, caregivers make up 45.7% of year-2 agent-days and are never hungry in year 2 (mean reserve 0.93 for everyone). V1 hunger is the founding transient: 1,459 of its 1,525 hungry days fall in year 1 Q1, and only 121 of them are caregivers. So the two physiologies differ precisely in what caregiving costs the caregiver. V2 makes nursing draw down the reserve (G10.5's "corrected nursing"). Under v1 it does not visibly do so.

Not yet separated: whether the limit is lactation demand outrunning a daily intake ceiling, or the fat-reserve accounting during nursing. The census records reserves, not intake. Separating them needs per-day intake against demand for caregivers, which is a diagnostic addition, not a model change.

## 6. Foundations to check before changing ecology

### 6.1 Animal life-history units (finding: a units mismatch)

From the code, by arithmetic, not from a run:
- **Durations are converted.** `ecology/traits.py` states life-history durations in months (`TRAIT_REFERENCE_TICKS_PER_YEAR = 12`). `animals.py` scales maturity, maximum age and breeding cooldown by `ticks_per_year / 12`. At 365 ticks/year a grazer matures at 852 days, breeds at most every 912 days, and lives about 26 years.
- **Per-tick rates are not converted.** `basal_cost`, `movement_cost`, `water_loss_per_tick_kg` and the 0.004 kg bite cap are applied once per tick at any timebase. At 365 ticks/year an animal therefore pays and eats about 30× more per simulated year than at the 12 ticks/year where G4 qualified it.
- **The two mismatched halves explain G10.4's finding.** The `reproduction_energy` stock is reached quickly at daily ticks and then waits behind a 912-day cooldown. That matches G10.4's "2,400–2,500 animal-days meeting every reproduction condition except the breeding interval".
- **The values are implausible even in months.** A 50 g grazer that matures at 28 months, breeds every 30 months with one young, and lives 27 years has a large mammal's life history. The values were tuned for G4 persistence at monthly ticks and carry no body-size reference.

Two separate corrections follow, and each needs owner authorization:
1. **Units (defect).** Express per-tick rates per day, or per unit time, and scale them with the timebase, exactly as durations are. This is a correctness fix. It must reproduce G4 at 12 ticks/year unchanged.
2. **Calibration (biology).** Set life history, metabolism and body mass from one allometric reference. This changes the world and is justified by body size, not by Agentus outcomes. The G3/G4 gates must be re-qualified.

Neither is a change to "raise animal reproduction to feed cognition". Hunting, predator viability and any animal-food result depend on both.

### 6.2 Physiology default

See section 5. The two physiologies give different founding transients and different late-life reserve dynamics. The choice of default changes what hunger means in every later census.

## 7. Owner decisions, with concrete consequences

### D1. Predation on Agentus (a code limitation must not become a biological rule)

What the code does now:
- Predators bite Agentus on contact (`biology._apply_predator_threat`, raising injury).
- Agentus is never a prey candidate (`animals._prey_candidates` lists animals only).
- Agentus remains go to `human.remains_cells`, a pool that no animal reads.
- So a predator can injure an agent but cannot gain from it.
- `tests/genesis/micro/test_micro_cannibalism.py` records this as *current behaviour, not a decision*.
- Under the old per-tick timebase the only predator starved in year 1 (G10.4), so the question was moot. **After the D2 units fix the predator survives, and the limitation is active.** Injury deaths of Agentus rose from 2 to 7 in the two-year census. That rise is attributed to predator bites on one smoke seed and is inferred for the rest. The predator cannot eat what it kills.

The options:
- **(a) Declare it a rule:** Agentus is not prey. The consequence is an injury source with no ecological cause, which would need its own justification. It would also be a biological claim with no basis in the model.
- **(b) Model predation on Agentus:** Agentus becomes a prey candidate, and remains become scavengeable carcass tissue under the same conservation path. The consequences:
  - a new mortality source;
  - remains enter the consumer element accounting;
  - predator viability depends on fixing 6.1 first.
- **(c) Remove the attack until (b) is decided.** The consequence is one less unexplained injury path. G10.4 encounter results that include predator bites would change.

**Recommendation:** record it now as an architectural limitation, not a rule, as this document does. Decide between (b) and (c) after 6.1. Do not take (a) without a biological argument.

### D2. Animal life history

There are two decisions (section 6.1): the units fix, which is a defect, and the allometric recalibration, which is biology. Consequences:
- G3/G4 re-qualification at 12 and 365 ticks/year;
- hunting yield;
- predator survival;
- D1.

**Decision (2026-10-07):** the units fix is authorized and **implemented** (`docs/architecture/D2_CONSUMER_TIMEBASE.md`).
- Results at 12 ticks/year are bit-identical; `per-tick-legacy` reproduces earlier runs.
- At daily ticks the predator survives for years instead of weeks.
- Herbivore births are unchanged, so the life-history bottleneck stands.

The allometric recalibration remains open and needs its own authorization.

### D3. Default physiology (`reference-v1` vs `reference-v2`)

Concrete differences measured here (4 seeds × 730 days):

| | reference-v1 | reference-v2 |
|---|---|---|
| founding reserve | ≈0.67 → hungry 50% of year 1 Q1 | 1.00 → no founding hunger |
| late hunger | none | 4.4% of year-2 days, mostly reserve < 0.25 |
| imitation tries | 18 | 46 |
| outcome | births 21, deaths 2 (injury) | births 19, deaths 0 |

**Recommendation:** section 5.1 shows that reference-v2's late deep drops occur only in caregivers, with food in view. Its hunger is a physiological signal of caregiving cost, not a scarcity signal. Before choosing it as the default, measure caregiver intake against demand, to confirm that the drops are physical (lactation outrunning a daily intake ceiling) and not an accounting artefact. If they are physical, v2 is the more faithful baseline. Either way, no census or experiment should read the hunger label as scarcity without the reserve bins and the caring split.

## 8. Proposed controlled experiments (not implemented)

Each arm changes one physical factor with a stated justification and a prediction recorded before running. Each arm keeps:
- the baseline arm unchanged and reproducible;
- conservation, ledger and determinism checks (smoke integrity checks on every run);
- opportunity counts reported separately from use (follow days, imitation tries and payoff) and from survival.

Design: 4+ seeds × 730 days; census plus the diagnostic outcome measures.

| Arm | Physical change | Justification | Prediction (recorded now) |
|---|---|---|---|
| E0 | none (baseline) | | As section 4. |
| E1 seasonal amplitude | Larger seasonal temperature/light amplitude through the existing climate latitude term, as a different latitude rather than a new mechanism | Real foraging populations live across a range of seasonality. The current amplitude is one point in that range. | More hungry agent-days in the trough, and more "no full day known" days. Follow opportunities are still rare unless food is also patchy. |
| E2 patchiness | Plant establishment conditioned on edaphic heterogeneity (soil depth / water holding derived from terrain) or dispersal-limited seed spread | Natural plant cover is clumped by soil and dispersal. Currently at least 91 of 256 cells hold an adult-day at all times. | Fewer cells with an adult-day in view. More "partial / none" days. The follow branch is reached more often. |
| E1+E2 | both | | Follow opportunities rise most here. Whether following pays is the actual experiment. |
| E3 founding group | Founders placed as co-resident groups (the same quadrant cells shared) instead of one per cell, at the same total number | Founding groups of foragers are co-resident. Separate cells are a consequence of `seed_initial_humans` assigning each member a different ranked cell. This is an initial condition, not an ongoing attraction rule. | Raises year-1 Q1 co-presence only. Little effect on imitation, because useful acts are rare at the source. |

Not proposed:
- higher animal reproduction (see D2: fix units, then calibrate);
- any rule that draws agents together;
- population size chosen to produce contact.

Order: decide D2 (units) and D3 first, because both change the baseline that E1–E3 are compared against. Then E2 and E1 singly, then E1+E2. E3 only if founding-period effects become a question.

## 9. What this means for G10.7

- G10.7a step 5 (measurement) is largely supplied by this census for opportunity. Transmission chains remain unmeasured.
- G10.7b (the costly call) stays paused. A signal is only worth modelling where the census shows information worth signalling, such as patchy food not in view. This world does not have that.
