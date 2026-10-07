# Testing tiers

Long multiseed runs are validation, not the debugging loop. Questions are answered at the smallest tier that can answer them, and only then confirmed at the next one up.

| Tier | What | Size | Wall time (4 vCPU) | Command |
|---|---|---|---|---|
| 1. Micro | One mechanism in a hand-built world of a few cells | 74 tests | ~2 s | `python -m qualification.genesis.tiers micro [topic]` |
| 2. Smoke | Production runs, every mechanism on, integrity and pathology checks | 3 seeds × 75 days (+1 unobserved rerun) | ~25 s | `python -m qualification.genesis.tiers smoke` |
| 3. Diagnostic | One question, 2+ arms, outcome comparison plus the smoke checks | 4 seeds × 180 days per arm (365 optional) | ~1.5–2 min for 2 arms at 180 days; ~4 min at 365 | `python -m qualification.genesis.tiers diagnostic <set>` |
| 4. Full | The existing 20 seeds × 730 days × 5 arms validation | 100 runs | ~1.5–2 h on Railway (8 vCPU, 3 parallel) | `python -m qualification.genesis.tiers full` |

**FAST DEVELOPMENT mode** runs micro then smoke: `python -m qualification.genesis.tiers fast` (about 30 s). Run it before every push. Run a diagnostic only for the question being changed, and the full tier only before claiming a result.

All commands run from the repository root with `PYTHONPATH=src:.`. On Railway, or any log-only runner, use `experiments/genesis/run_tier_railway.sh` with `HRM_TIER=fast|smoke|diagnostic|full` and `HRM_TIER_ARGS` (for example `HRM_TIER=diagnostic HRM_TIER_ARGS="infant --days 365"`). The full tier still uses `run_g10_3_railway.sh`, which is unchanged.

## 1. Micro scenarios — `tests/genesis/micro/`

`_scenario.py` builds a real world, clears every pool, places exactly what the test names, and advances the real `evolve_agentus_step`. Production code is never patched. The scenario edits initial state only, and world physics the test does not ask about is held neutral (22 °C, no rain or fire).

| Topic | File | Questions |
|---|---|---|
| thirst | `test_micro_thirst.py` (8) | Drinks local water. Reaches water one cell away. Walks to remembered water. Does not know unseen distant water. The more urgent need (water or food) wins. A cell meeting both needs beats either alone. No repeated water seeking when hydrated. |
| food | `test_micro_food.py` (11) | Only plant tissue known at start, newborns included. Nearby known food is eaten. Unknown seed is tasted, survived and learned. Meat is learned only by tasting. Seeing it eaten (same cell only) gives no value. Rotten meat stays hazardous and is then avoided. Wood never becomes food. Partial food is not abandoned, a richer visible patch is chosen, and a trickle below the giving-up level is left. |
| hunting | `test_micro_hunting.py` (5) | An animal in another cell is not offered. Capture needs approach, with real costs and both outcomes. A kill yields tissue exactly once. Tissue spoils faster warm and conserves mass. A held stick extends reach; one lying nearby does not. |
| stone | `test_micro_stone.py` (6) | A stone must be encountered before pickup. Carried stone is conserved. Over-heavy stones are not offered. Striking conserves lithic mass. Sharp edges only where fracture rules allow. Blunt stone never cuts, and edges wear. |
| fibers | `test_micro_fibers.py` (5) | Extraction needs the source in this cell. Split, twist, weave and bind conserve material. Strength and wet sensitivity differ by source. A binding can hold, slip or break. Meaningless repeats cost and are not reinforced. |
| learning | `test_micro_learning.py` (7) | Value from experienced benefit. Delayed credit through the tool's history. Failed capture is learned as negative. A no-payoff world forms no habit. A sated agent stays rested enough to explore, and daily walking reaches a steady fatigue. |
| infant_care | `test_micro_infant_care.py` (9) | A provisioned caregiver feeds the infant. Nursing transfers energy, water and mass. No caregiver or a caregiver elsewhere means no provisioning. Infant starvation reproduces in isolation under reference-v1 and not under reference-v2. A separated dependent walks one cell a day, and a carried one stays with its caregiver. |
| social | `test_micro_social.py` (11) | Only visible acts and consequences travel; observers appraise by their own values; seen eating changes readiness to taste, not value; G7 recipe transfer only with its legacy flag. |
| memory | `test_micro_memory.py` (8) | Witnessed acts and meals are remembered with visible fields only, by agents in the same cell, dependents included; the bound keeps the newest 32; no decision code reads the memory. |
| cannibalism | `test_micro_cannibalism.py` (4) | Diagnostic only: where Agentus remains go, whether they are a food kind, perceived or tasted, whether Agentus are capture targets. Prints a report. |

**Known defects are recorded as strict `xfail`s.** They are listed by `-rx` on every run and turn into failures the moment behaviour changes, so a fix is noticed. The first three (partial-food abandonment, dependent teleportation, fatigue saturation) were fixed in G10.6. They are now ordinary tests, plus tests that reproduce the old behaviour with `agentus_behavior_integrity_enabled=False`.

## 2. Smoke — `qualification/genesis/smoke.py`

The default arm is `v1`: capacities, thirst, interactions, learning and observation on, with production physiology. Seeds are `agentus-demography-a`, `agentus-demography-b` and `agentus-g10-4-01`, over 75 days. Options: `--days`, `--seeds`, `--arm v1@reference-v2`, `--json`.

The shared observer (`qualification/genesis/tier_observer.py`) wraps `interactions.execute`, `interactions.choose` and `planning._thirst_destination`. It only looks, and returns results unchanged. Smoke reruns the first seed without the observer and requires an identical ledger digest.

**FAIL (exit 1):**
- crash;
- invalid ledger chain;
- NaN or inf anywhere in state;
- a negative value in any `*_kg` field;
- element, water or lithic balance error above 1e-6 relative;
- remote pickup, capture, tool or target, re-derived independently of the production guards;
- duplicate kill, or a kill-count mismatch;
- more than 3 interactions in one agent-day;
- a no-op interaction repeated as a learned habit 10+ times by one agent (no extinction: a superstition loop);
- a dependent moving more than one cell on its own (not carried);
- a thirst move more than one step, to an unperceived cell, or over hunger that would kill sooner;
- an adult dehydration death with water in view;
- the observer changing the run.

**warn:**
- an adult starved with ≥5 kg of plant or seed in its cell (death context `energy|adult|food_in_own_cell`);
- an adult dehydration death with water remembered;
- population below half of founders;
- fatigue above 0.8 on more than 25% of agent-days;
- no-op share above 50%;
- a no-op chosen as a habit at all, before it extinguishes (for example, delayed credit from a kill reaching the hammer stone's earlier strikes);
- dependents apart from their caregiver on more than 5% of dependent-days.

## 3. Diagnostic — `qualification/genesis/diagnostic.py`

| Set | Arms (reference first) | Question |
|---|---|---|
| `thirst` | `v0-nothirst`, `v0` | Does the thirst drive behave? Defaults to 365 days: at 180 days the arms are identical on the diagnostic seeds, because the pre-thirst dehydration deaths come later. |
| `hunting` | `plant_diet`, `v1` | What do animal food and capture add? |
| `interactions` | `no_interactions`, `v1` | What do material interactions add? |
| `learning` | `no_recall`, `v1` | Place memory; reports repeated use, transmission and food adoption. |
| `infant` | `v1`, `v1@reference-v2` | Caregiving and energy budget. |
| `capacities` | `v0`, `v1` | All capacities. |
| `integrity` | `v1-preg106`, `v1` | G10.6 behavioural/locomotion integrity. |
| `observation` | `v1-g104obs`, `v1` | G10.7a: only visible acts and consequences travel. |
| `memory` | `v1-nomem`, `v1` | G10.7a step 2: witnessed memory; outcomes must be identical. |
| `custom` | `--arms ...` | Any comparison. |

Arm suffixes: `-nothirst` (thirst off), `-preg106` (G10.6 off), `-g104obs` (G10.4 observation), `-nomem` (no witnessed memory), `@reference-v2` (physiology). There is no arm that disables value learning alone. `learning` compares place memory and reports the learning measures for both arms.

Reported per arm:
- survivors and adults;
- births;
- deaths by cause, with death context (stage; water or food in view);
- hunting attempts, kills, fresh tissue eaten, animals left;
- intake by kind and food kinds valued;
- interaction counts and repeated beneficial use;
- observed transmissions and food adoptions;
- fatigue-blocked share;
- ledger validity, balance error, FAIL and warn counts;
- the delta against the reference arm.

Use `--days 365` for slower questions. Each run holds its replay ledger in memory, about 0.4 GB per 180 days.

## 4. Full validation

This is unchanged: `experiments/genesis/run_g10_3_railway.sh`, with 20 seeds × 730 days × arms `v0 v1 plant_diet no_interactions no_recall`, aggregated by `aggregate_capacity_runs.py`. It is the only tier that can support claims about multi-year survival, generational turnover, births and orphaning across seasons, or learning that takes more than a few months to pay off.

## Advancement rule (owner decision, 2026-10-07)

Perfect long-horizon survival is **not** a prerequisite for a new capability. A mechanism advances when its own physical and integrity contract holds at the micro and smoke tiers (and a targeted diagnostic where outcomes matter), even if the ecology still has unsolved mortality:

- **Thirst:** acts on local or remembered water only, competes with hunger, and does not cause water-seeking regressions.
- **Hunting:** requires approach and physical contact. No remote capture and no duplicate kill.
- **Omnivory:** is a capability, not knowledge. Only plant tissue is known at birth. Other kinds are learned by tasting or observation.
- **Stone and fibres:** obey material constraints. Mass is conserved, edges arise only where the fracture rules allow, and every action needs a held tool and a local source.
- **Ledgers:** valid chains, element, water and lithic balance, and determinism.

Survival and demography outcomes are reported as findings, not used as gates. The full 730-day tier is run to support claims about long-run outcomes, not to unblock work.
