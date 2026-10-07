# G10.4 — Survival bottlenecks: thirst, physical hunting, delayed credit, observation

G10.3 added abilities but did not show learned technology or a sustainable population. This phase works on the bottlenecks that evidence identified, in order of impact. Every causal change is versioned. With thirst opted out and capacities off, ledgers match the pre-G10.4 `main` exactly.

| # | Change | Kind | Switch |
|---|---|---|---|
| 1 | Thirst as a planning drive | **Baseline correction**: the body had a need its decisions could not see | On by default with cognition; `agentus_thirst_enabled=False` reproduces pre-G10.4 |
| 2 | Animal population diagnosis | Diagnosis only; no ecology change | — |
| 3 | Physical approach and contact before capture | Capacity correction (removes an unearned opportunity) | `capacity-v2` |
| 4 | Delayed credit through object history; warmth as reward | Cognition extension | `capacity-v2` |
| 5 | Measuring repeated beneficial use; learning by observation | Measurement plus cognition extension | `capacity-v2` |

The capacity model version is now `capacity-v2`. G10.3 evidence remains tied to its recorded commits.

## 1. Thirst (baseline correction)

Thirst is a normal biological signal, not a solution handed to Agentus. It is therefore part of the baseline, not an experimental arm. It is on by default wherever Agentus cognition is enabled, and the canonical config records it (`agentus_thirst_enabled: true`). Setting it to `False` restores the earlier planner and its earlier fingerprints, for reproducing old results only.

Validation is limited to implementation sanity (`experiments/genesis/run_thirst_sanity.py`):
- thirst competes with hunger rather than overriding it;
- it uses only perceived or remembered water;
- dehydration deaths drop for the right reason;
- no new pathological behaviour appears.

It is not tested as an open research question.

**Diagnosis (v0, seed A).** Every adult dehydration death followed 5 or more days standing on a cell with **0 kg** of water, while an adjacent cell held **30–68 t**. Most of these adults had full energy reserves, so the hunger rule never fired. The default score weighted water at 0.002 per kg and food dominated.

A separate failure: orphans aged about 1.2–1.6 years died on wet cells. They are still fully dependent (dependence lasts 2 years), and only nursing supplies their water. That is the dependence rule, not the planner, and it is unchanged here.

**Mechanism.**
- **What the body senses.** Agents sense their reserves in days: `hydration_days` from body water above the lethal floor, and `energy_days` from energy over basal cost. Declared assumption: interoception of depletion is innate. The location of water is not sensed beyond the usual perception radius.
- **When thirst acts.** When the current cell cannot refill today's need, the agent moves:
  1. to the nearest visible cell that can (preferring one that also has enough food);
  2. otherwise, toward a remembered place that held enough water;
  3. otherwise, toward the least-visited neighbour.
- **Hunger first when it is closer to killing.** If hunger is pressing and the energy reserve would run out sooner, the existing hunger rules decide instead.
- **Physiology is unchanged.**

**Check.** Seed A, v0 with thirst: 0 dehydration deaths (v0: 10), and 12 Agentus alive at day 730 (v0: 2). Multiseed results are in the evidence summary.

## 2. Animal population (diagnosis only)

This used the experiment world without Agentus, over five years, on seeds a and b.

- **Founding size.** Every world starts with exactly 5 animals (2 grazers, 2 browsers, 1 predator) of 0.012 kg each. The number does not depend on world size, and the mass does not scale with `material_scale_factor` (`animals.py: build_consumer_state`, `seed_initial_consumers`).
- **The predator starves in year 1** on both seeds. There is no predation afterwards.
- **Herbivores are not food-limited.** Edible plant tissue averages about 60 t. Herbivores spent roughly 2,400–2,500 animal-days meeting every reproduction condition except the breeding interval.
- **Life history is the bottleneck.** Life history is scaled from a monthly reference: at daily ticks a grazer matures at 852 days, breeds at most every 912 days, and has one young. That is a large mammal's life history attached to a 50 g body.
- **Outcome.** The population grows from 5 to 13 animals (0.7 kg) in five years.

**Conclusion.** Hunting cannot become a meaningful food source until animal founder numbers, body size relative to material scale, and life-history timing are recalibrated. That changes environmental resources, so it **requires the owner's authorization** and is not changed here.

## 3. Physical approach and contact

Sharing a cell no longer grants a capture attempt. The grid declares no cell size, so encounter geometry is declared here:

1. **Separation.** The animal starts 10–60 m away.
2. **Stalk.** Each metre closed carries a detection hazard of `(0.02 + 0.02·perception_radius) × (1 + fatigue)`.
3. **Chase.** A detected animal flees toward cover 25 m away at `(6 + perception_radius) m/s × (0.4 + 0.6·condition)`. The agent sprints at 7 m/s × capability for at most 12 s. It closes the gap only if it is faster and reaches the animal before cover.
4. **Contact.** Contact means reach: arm 0.7 m plus any held shaft.
   - A held striking head kills if its impact energy (with a 0.5–1.0 geometry draw) is at least `40 J/kg × prey mass + 1 J`.
   - Bare hands hold the animal with probability `0.6 × capability × (1 − 0.3·condition)`.
   - Predators bite on contact.
5. **Cost.** Effort is `5 + 0.04 kcal/m walked + 0.15 kcal/m sprinted`. Fatigue rises with sprint time.
6. **Escape.** An escaping animal moves one cell away.

## 4. Delayed credit

**Object history.**
- Every object records the interactions that made it, shaped it, or picked it up, up to 16.
- An object made from others inherits their histories and the history of the tool used.
- Putting an object down is not recorded.

**Crediting.**
- When an interaction yields benefit, the benefit is credited through two routes, each key once, at the larger share:
  - the last 8 interactions in time, decay 0.7;
  - the history of the object used, decay 0.8 by recency, with no time limit.
- So the actions that prepared a tool can be reinforced however long before its first use they happened.

**Warmth as reward.**
- The cold-stress energy saved by wearing a surface is computed each tick: thermal cost without the insulation minus thermal cost with it.
- It credits wearing and the surface's making-history.
- One cold day saves about 60 kcal, about 3% of daily need, so the benefit accrues over days of wear rather than in one step.

## 5. Repeated use and observation

**Repeated beneficial use.** An interaction chosen *because its learned value is positive* is counted per interaction and per agent. That separates practice from exploration.

**Observation.** Declared assumption: beneficial outcomes are visible; failures and internal costs are not.
- An agent in the same cell that sees an interaction pay off updates its own expectation of that interaction, at half the observed reward.
- An agent that sees another eat a kind repeatedly without harm adopts a cautious prior: half the observed energy per kg. Kinds it already has a value for are unchanged.

## Not changed

- Resource quantities.
- Animal ecology.
- Physiology parameters.
- Infant dependence.
- Seed and plant dynamics.
