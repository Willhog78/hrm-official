# Predator reproductive support — 2026-10-09

The opt-in `reserve-backed-v1` model lets a predator's actual meal and finite energy reserve support subsequent non-feeding days. It removes the daily-kill requirement without changing hunt opportunities, success probabilities, animal sizes, food supplies, movement, maturity, reproductive energy, offspring transfers or cooldowns.

## Rule

A successful prey meal records `predator_last_meal_epoch`. Until the energy reserve can no longer cover another tick of basal maintenance, elapsed supported ticks accumulate even on days without feeding or visible prey. Unsupported days reset the support count. Initial seeded energy alone does not count as a feeding history. Newborn predators start without a meal record or inherited support.

Reproduction still requires the existing maturity, energy, body-mass, support-duration and cooldown conditions, plus a locally visible live herbivore. Prey already killed in the current tick cannot certify habitat support. A previously consumed meal can bridge a gap in prey contact; finite reserves pay the gap. No arbitrary meal grace period is introduced.

The support-duration threshold remains the larger of five reference months and one third of the existing reproductive cooldown. For stalkers that is about 30 months: 30 ticks at 12 ticks/year, 912 at 365. This is a correction to support accounting, not a recalibration of stalker biology. Herbivore support logic is unchanged.

The default remains `consecutive-feeding-legacy`. States without `predator_support_model` retain the original consumer behavior. Configurations selecting `reserve-backed-v1` receive a distinct fingerprint and state key. Use `v1-reservepredators` to isolate this correction from the old nursing baseline, or `v1-remainingmilk-reservepredators` to combine it with the nursing correction. No Railway settings or saved production checkpoints are changed.

## Controlled reachable-prey test

A 2×2 finite habitat contains one mature stalker and twelve browsers, with existing finite plant/water stocks. The real movement, opportunity draws, hunt success, prey consumption and evolution functions run for four years. Climate and producer growth do not advance in this isolated consumer test. No hunter teleportation, forced catch or food injection is used.

| Time step | Old first predator birth | Fixed first predator birth | Actual first meal | Fixed support duration at birth |
|---|---|---|---|---|
| 12 ticks/year | None | Epoch 29 | Epoch 0 | 30 ticks / 2.5 years |
| 365 ticks/year | None | Epoch 952 | Epoch 41 | 912 ticks / 2.499 years |

At either time step the original maximum consecutive support count is one; the fixed habitat ends with one founder and one world-born stalker. Tests also cover finite energy, failed support, no meal history, no local prey, already-killed prey, immaturity, cooldown, herbivore isolation, configuration/state identity and exact matter/water accounting through a real predator birth.

## Ten-year unchanged-world comparison

Both arms hold nursing at `remaining-demand-v2`; the only configuration difference is predator support. Four seeds run from initial state for 3,650 days each. The corrected rule does **not** restore predators in these worlds during that period.

| Seed | Predator outcome in both arms | Human alive / births / deaths at year 10 | Other animals at year 10 |
|---|---|---|---|
| a | Founder starves in year 3 | 21 / 13 / 0 | 8 browsers |
| b | Founder captured by Agentus on day 17 | 29 / 21 / 0 | 16 browsers, 16 grazers |
| c | One founder alive; no predator offspring | 18 / 10 / 0 | 8 browsers, 8 grazers |
| d | Founder starves in year 2 | 48 / 40 / 0 | 12 browsers |

All 40 paired yearly outcome records match in population, generations, human births/deaths, animal counts, captures and imitation totals. The first five years of the nursing-only arm also reproduce the published nursing comparison. This change fixes reproductive support accounting, but these worlds still have a predator encounter/habitat problem.

Seed c's year-10 founder has age 3,656 ticks (maturity 1,825), energy 45.401 (required 24), dry body mass 0.045463 kg (required 0.03825), and 3,199 supported ticks (required 912). Its cooldown is satisfied; `last_reproduction_epoch` remains the original -1,000,000. Its last actual meal was at epoch 451.

Inference from that final state and the production gate: local live prey is the remaining failed condition at the reproduction evaluation. Final prey positions were not exported separately. The finite energy reserve permits the long interval without a new hunt under the existing tiny animal/metabolic calibration; that calibration is unchanged. A separate seed-c replay reproduces all ten yearly outcomes and retains the final predator state.

The annual support maximum reports the pre-update counter through the observer (3,198 in year 10); the final persisted counter is 3,199. These refer to adjacent points in the same tick.

## Validation

- Full suite: 344 tests passed in 300.81 seconds, including twelve new predator regressions.
- Fixed combined-arm smoke: three seeds × 75 days, zero failures and warnings; valid ledgers, observed/unobserved digest equality and maximum relative element balance error approximately 1e-15.
- Each of eight replay arms passes complete 30-day scheduler-state equality before and after diagnostic instrumentation/acceleration. This verifies the replay schedule; long-run production ledger digests are not reconstructed.
- Original consumer kernel versus modified kernel with no opt-in state key: exact complete consumer/producer/matter equality on every step for four years at both 12 and 365 ticks/year (48 + 1,460 steps).
- Controlled predator reproduction conserves tracked elements and water. Source diff whitespace check passes.

## Reproduce

```sh
python -m pytest tests/genesis/test_predator_support.py
python -m qualification.genesis.tiers smoke --arm v1-remainingmilk-reservepredators
python experiments/genesis/run_generations_diagnosis.py --seed c --arm v1-remainingmilk --years 10 --owned-state --spatial-index --out runs/predator-baseline
python experiments/genesis/run_generations_diagnosis.py --seed c --arm v1-remainingmilk-reservepredators --years 10 --owned-state --spatial-index --out runs/predator-fixed
```

Repeat the replay commands for seeds a, b, c and d. The ten-year comparison holds nursing at `remaining-demand-v2` in both arms. The dated evidence JSON preserves annual outcome/diagnostic records, terminal predator deaths, controlled results and validation records.
