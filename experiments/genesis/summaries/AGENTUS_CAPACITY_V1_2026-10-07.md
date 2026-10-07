# Agentus capacity model v1 — first multiseed evidence (October 7, 2026)

**Bottom line.** Agentus can now physically eat seeds and animal tissue, kill animals, fracture stone, extract and twist fibers, bind objects, and wear interlaced surfaces. All of this conserves tracked material and replays deterministically. Over two years on four seeds, none of it produced a reliable change in survival. In every arm, survival is limited by dehydration: the planner still has no thirst signal. Animal food is negligible at the current animal scale. No learned tool use was observed.

## Setup

- **Experiment:** `experiments/genesis/run_agentus_capacity_multiseed.py`.
- **Where it ran:** the Railway runner (`hrm-survival-affordances-runner`). Results were printed to the log as `CAPACITY_RESULT` lines; transcribed values are in `agentus_capacity_v1_2026-10-07.json`.
- **World:**
  - 16×16 cells, daily ticks, 730 days;
  - material scale 1000;
  - four populations of two founders;
  - same seeds as the earlier demography experiments.
- **Code versions:**
  - capacity arms ran at commit `d6d3552`;
  - v0 ran at `84c33a1` (its code path is unchanged since then).
- **Resources and physiology:** resource quantities, plant and animal ecology, physiology, and every pre-existing parameter are unchanged.

| Arm | Description |
|---|---|
| v0 | Capacity model off. This is the model on current `main`. |
| v1 | Capacity model v1. |
| plant_diet | v1 without sampling unknown foods, so the diet stays plant tissue only. |
| no_interactions | v1 without manipulation or capture. |
| no_recall | v1 without travel toward remembered food. |
| null | v1 with all three ablated. Control for anything else the capacity code changes. |

## Results (sums over seeds a/b/c/d)

| Arm | Survivors (a/b/c/d) | Births | Deaths | Dehydration | Energy | Injury | Breeding pairs at end |
|---|---|---:|---:|---:|---:|---:|---:|
| v0 | 2/1/3/2 = **8** | 19 | 43 | 37 | 6 | 0 | 0 |
| null | 2/1/3/2 = **8** | 19 | 43 | 37 | 6 | 0 | 0 |
| v1 | 1/2/2/8 = **13** | 23 | 42 | 39 | 1 | 2 | 1 |
| plant_diet | 5/4/1/1 = **11** | 25 | 46 | 37 | 9 | 0 | 2 |
| no_interactions | 1/0/0/1 = **2** | 22 | 52 | 51 | 1 | 0 | 0 |
| no_recall | 0/4/2/8 = **14** | 19 | 37 | 35 | 0 | 2 | 1 |

**The null arm matches v0 per seed:** the same survivors, births and causes of death. A day-by-day comparison on seed A showed no material divergence in 500 days. The control is valid. Everything the capacity arms change comes from the three behaviors under test.

**Interpretation.**
- Arm-to-arm differences go in both directions and do not repeat across seeds. For example, v1 is worse than v0 on seeds a and c and better on d.
- Removing interactions gives the lowest total, but removing new foods or recall does not.
- **No consistent pattern:** with four seeds and two founders per population, this looks like variation between individual trajectories, not a capacity effect.
- **No arm shows a reproductively viable outcome.** A breeding pair surviving in one population is the most any run achieved.

### Diet: food available vs eaten

| Arm | Plant tissue eaten (kg) | Seed eaten (kg) | Fresh animal tissue eaten (kg) | Decayed tissue eaten (kg) |
|---|---:|---:|---:|---:|
| null (= v0) | 27,440 | 0 | 0 | 0 |
| v1 | 18,156 | 8,129 | 0.28 | 0.11 |
| no_interactions | 17,930 | 8,035 | 0.006 | 0.019 |
| no_recall | 19,049 | 8,589 | 0.32 | 0.09 |

- **Availability.** Edible plant tissue averaged about 60 t world-wide and seeds about 50 t, with seasonal lows near 0.8–1.1 t of plant tissue and 0 seed.
- **Seeds.** Seeds became about 30% of dry intake wherever agents sampled them. They replaced plant tissue rather than adding to total intake.
- **Animal tissue.** In two years, all Agentus in the v1 arm together ate 0.28 kg of animal tissue, about 1,200 kcal. That is less than one adult's daily need. Live animals in the world total 0.1–0.3 kg (2–6 animals of 12–85 g).
- **Spoiled and woody material.** Decayed tissue and wood were sampled, gave nothing, caused small harm (decayed), and were then avoided.

### Interactions and material pathways (v1, four seeds)

- **Capture.**
  - 48 attempts, 10 kills, 38 escapes.
  - In v1 seeds b and c, in no_recall seeds a, b and c, and in plant_diet seed c, Agentus killed every animal in the world. Animal reproduction cannot absorb even 3–4 kills.
- **Stone.**
  - 41 fractures yielded 6 flakes with edge sharpness ≥ 0.4. Most fractures produced blunt pieces, as the fracture rules intend.
  - Cuts on carcasses were rare (3–7 per run).
- **Fibers, binding, surfaces.**
  - 360 strands extracted.
  - 3 bindings held, against 50 failures, mostly "too short" or "too stiff". No binding was later loaded to failure.
  - 43 interlaced surfaces were made; 1 was worn.
- **Cost.**
  - About 15,000 kcal of interaction effort in total, under 0.03% of energy intake.
  - Interaction injuries were small (0.06–0.37 injury units per run); two deaths in v1 seed d were from injury.
- **Learning.**
  - At day 730, no living Agentus held a positive learned value for any interaction.
  - Some living agents had learned that seeds, and in a few cases fresh tissue, are food.
  - Every material event above came from costed exploration. None repeated because it paid.
- **Ledgers.** All ledgers valid. Lithic ledger error ≤ 3×10⁻¹³ kg. Element and water closure is tested in `tests/genesis/test_g10_3_agentus_capacities.py`.

## A confound found and removed during this experiment

The first batch, run on commits up to `cfd6230`, showed all capacity arms well above v0: 21–29 survivors against 8. The null arm, added to explain that, also reached 23.

**Cause.** Plant tissue had been given a 99 kg/day gathering limit as a stand-in for "unlimited". Perception applied it, so every cell with more than 99 kg of plant tissue looked equally rich. The planner's small water term then broke the tie, and agents drifted toward wetter cells. That is an undeclared planner change: effectively a thirst signal, which is a decision reserved for the project owner.

**Fix.** It was removed in `d6d3552`. A regression test fails on the old code and passes now. The table above is the corrected result. The superseded survivor counts are kept in the JSON under `superseded_survivors_with_planner_confound` and **must not be cited as capacity effects**.

**What the confound does show.** Even crude water-awareness in movement roughly tripled two-year survivors. That is strong evidence about where the binding constraint lies.

## What this evidence supports

- **Supported:**
  - The new capacities exist in the live world.
  - They are reached through exploration and have physical consequences.
  - They conserve material and replay deterministically.
  - They do not by themselves change survival in this world and time span.
- **Not supported:**
  - Any claim that omnivory, stone or fiber use improves survival.
  - Any claim that Agentus discovered tool use, binding or clothing. Events occurred but were not repeated or transmitted.
  - Any conclusion about real humans or about civilization.
- **The limiting factors, in order:**
  1. Water-seeking in the planner. Dehydration accounts for 37 of 43 deaths in v0 and 39 of 42 in v1.
  2. The 18-year maturity versus a 2-year run.
  3. Too few founders per population.
  4. Animals scaled far below Agentus.

## Pending decisions (not changed here)

1. A planner thirst signal, as already raised in the plant-lifecycle report.
2. Animal abundance and body size relative to `material_scale_factor`.
3. More seeds per arm. Railway makes about 20 seeds per arm practical. Four seeds cannot separate effects of this size from trajectory variation.
