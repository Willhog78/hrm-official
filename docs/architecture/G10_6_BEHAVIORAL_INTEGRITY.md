# G10.6 — Behavioural and locomotion integrity

The fast test harness (`TESTING_TIERS.md`) exposed three causal-model defects. Food that was physically available was ignored. Children violated space. Ordinary walking mathematically destroyed the capacity to manipulate the world. These are corrections to how the model works, not survival aids.

All three are a **baseline correction**, switched on by `agentus_behavior_integrity_enabled`:
- It is default **on** wherever human biology runs, and the canonical config records it as `agentus_behavior_integrity: "g10.6"`.
- `False` reproduces pre-G10.6 runs exactly. Each defect keeps a micro test that reproduces it with the flag off.
- The diagnostic arm suffix `-preg106` (for example `v1-preg106`) turns it off for comparisons.

## 1. Partial food is not abandoned

**Defect.** When no visible cell covered a full day's need, the hungry-exploration rule moved the agent to the least-visited neighbour, even when the only reachable food was where it stood. The move happens before eating, so the agent left food for empty ground and could starve beside a known patch.

**Correction** (`planning.choose_destination`):
1. Remembered food that covers a full day still comes first (unchanged).
2. Next, a hungry agent goes to, or stays at, the richest visible cell, provided that cell yields at least `PARTIAL_FOOD_GIVING_UP = 0.25` of the daily need.
3. Only below that level does it explore.

The giving-up level is declared, by analogy with giving-up density in foraging theory: a patch is left when its yield falls below what is worth staying for. The yield used is the agent's own `expected_food_kg`, which reflects learned values and the hand-access limits, so nothing global is consulted.

## 2. Dependents move physically

**Defect.** A dependent child's destination was its caregiver's cell, with no distance limit. A child separated by any distance arrived in one day.

**Correction** (`biology.evolve_agentus_step`):
- **Carried.** A dependent that started the day in its caregiver's cell is carried and ends the day wherever the caregiver walked.
- **Separated.** A dependent that did not start with its caregiver moves one cell toward it per day, x first, then y.
- **Order.** Dependents act after everyone independent. Births are named `human-b…` and founders `human-g…`, so id order alone processed most children before their mothers moved. With the new order, carrying works, and nursing happens after the caregiver has eaten that day.

The smoke and diagnostic observer fails any run in which a dependent moves more than one cell without being carried.

## 3. Fatigue recovers with sleep

**Defect.** Each move added 0.08 fatigue and each day without movement removed 0.04. Interactions add 0.02 each, and sprints add more. Interactions stop above 0.8. An agent that walked on more than a third of days saturated at 1.0 and could not interact at all. In v1 production runs, 20–49% of agent-days were blocked.

**Correction** (`biology._apply_physiology`):
- The day's load is added, then a night's sleep removes a fraction of the total: 25% after a walking day, 40% after a resting day.
- Daily walking now settles at 0.08 × 0.75 / 0.25 = 0.24.
- Walking plus three interactions a day settles at about 0.42.
- Exhaustion, and the block above 0.8, now need genuinely heavy exertion such as repeated sprints.

The recovery fractions are declared values. No physiology parameter (energy, water, mass) changed.

## Evidence (fast loop only; no long batch)

**Micro: 56 pass, 0 xfail.** The three former strict xfails now pass. New tests cover:
- moving to richer partial food;
- leaving a trickle below the giving-up level;
- a carried child following a walking mother;
- the steady state of daily walking;
- reproduction of each old behaviour with the flag off.

**Smoke: v1, 3 seeds × 75 days.**
- No fails or warnings. The observed and unobserved ledgers are identical.
- Fatigue-blocked agent-days fell from 33–49% to **0%**.
- Interactions rose from 53–72 per run to 96–100.

**Diagnostic `integrity`: `v1-preg106` vs `v1`, 4 seeds × 180 days.**

| Measure | v1-preg106 | v1 |
|---|---|---|
| Fatigue-blocked agent-days | 27% | **0%** |
| Interactions | 538 | 750 |
| Capture attempts / kills | 8 / 1 | 13 / 3 |
| Repeated beneficial use | none | first instances: grasp heavy stone, strike stone on stone, separate and release plant strand, twist strands |
| Deaths (all seeds) | 1 adult energy, 1 dependent injury | 1 dependent injury |
| Survivors (mean) | 10.5 | 10.5 |

Survival is reported, not gated (see the advancement rule in `TESTING_TIERS.md`).

**Finding surfaced by the correction.** With fatigue no longer suppressing action, delayed credit becomes visible. In one run, a kill with a heavy stone credited that stone's history, which included an earlier stone-on-stone strike. The agent repeated the unproductive strike 5 times, at 8+ kcal each, before its value extinguished. This is ordinary credit assignment followed by extinction, not a loop. The smoke tier now warns on any no-op habit and fails at 10 repeats by one agent.
