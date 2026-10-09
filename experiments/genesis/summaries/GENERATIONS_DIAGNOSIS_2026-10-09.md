# Thirty-year generations diagnosis — 2026-10-09

The birth droughts are contact failures. Predator replacement is blocked by an inappropriate consecutive-feeding requirement. The child deaths expose nursing allocation and timing problems. The zero immediate-imitation-payoff counter does not establish that social learning failed.

## Evidence and scope

Baseline: `d36b5a8c6f067954dac57fa8526b48bea3665d25`; production configuration `v1`, seeds `agentus-demography-a` through `d`. Primary comparison: deployment `bffa7184-0df5-4e1d-9079-5bc8368a5ff9`, all 120 Railway yearly records.

The diagnostic replays call the same evolution functions in the same order, retaining the production scheduler’s old/new climate boundary. Each seed passed complete daily-state equality against the normal production runner for 30 days before observation and again with the diagnostic callbacks. All 120 annual population, generation, animal, cumulative birth/death, capture and immediate-imitation totals match Railway.

Acceleration is confined to private diagnostic replay: exclusively owned state buffers, exact animal-position counts and coordinate lookup caches. Support-query equivalence is checked against the original function at yearly boundaries. Replays consume private year-25 diagnostic snapshots for their final five years. These are separate from the Railway volume/checkpoints. Production source, configuration and Railway start commands were not changed.

The diagnostic replay does not reconstruct or verify the production replay-ledger digest. Per-agent imitation tags restart at diagnostic resume; the report therefore uses persisted cognition and actor-level repeated-act records for the learning conclusion. Ten existing imitation micro-tests passed by direct execution; the full test suite was not run.

Reproduce from the repository root: `python experiments/genesis/run_generations_diagnosis.py --seed c --years 30 --owned-state --spatial-index`; repeat for a, b and d. Omit the acceleration flags for the reference diagnostic path. The accompanying dated evidence JSON preserves all annual diagnostic counters, birth eligibility, terminal infant traces and the cited seed-c cognition entries.

## Final outcomes

| Seed | Alive | Gen 0 / 1 / 2 | Births | Deaths | Captures | Immediate imitation tries / paid |
|---|---:|---|---:|---:|---:|---|
| a | 80 | 8 / 39 / 33 | 73 | 1 | 3 | 444 / 0 |
| b | 91 | 8 / 34 / 49 | 87 | 4 | 2 | 283 / 0 |
| c | 25 | 8 / 9 / 8 | 17 | 0 | 28 | 70 / 0 |
| d | 127 | 8 / 53 / 66 | 127 | 8 | 2 | 593 / 0 |

## 1. Birth shutdown and restart

Seed c: all 10,950 adult-female days in years 26–30 failed `no_adult_male_in_cell`. In years 27–30 that was the sole failed condition on every day. Year 26 also included 30 energy failures and 55 cooldown failures; these overlapped the contact failure. Food depletion, death and an age cutoff do not explain this shutdown.

The first qualifying world-born males enabled the restart in year 19 in a, b and d, and year 20 in c. Seed c’s first world-born adult was female; its first qualifying world-born male matured in year 20. The earlier report’s statement that all four restarted births in year 19 was incorrect.

At epoch 6974 (year 20), seed c’s only qualifying male for `human-g00000006` was her son `human-b00000009`. That same male was the only qualifier for his maternal sister `human-b00000008`. Seed d also has a measured founder birth enabled solely by her son in year 19.

The code checks only whether an adult male is in the same cell. It assigns no father, records no paternal ancestry, checks no kinship, and models no inherited genetic consequences. These are eligibility traces, not recorded paternity. The run establishes descendant births but cannot establish genetic viability.

Movement is directed by food, water, memory and other existing rules; the reproduction condition does not itself create mate-seeking behavior. Females and males can remain healthy in different cells indefinitely.

Sources: `human/biology.py`, `_offspring` and the reproduction block in `evolve_agentus_step`; `human/planning.py`, `choose_destination`.

## 2. Predator losses and replacement

| Seed | Predator loss | Measured circumstances |
|---|---|---|
| a | Starvation, epoch 1035 (year 3) | Two herbivores alive, none within predator perception |
| b | Agentus capture, day 17 | The predator was one of the two year-1 captures; the other was a grazer |
| c | Starvation, epoch 8253 (year 23) | 423 herbivores alive, none within predator perception |
| d | Starvation, epoch 687 (year 2) | Two herbivores alive; one visible on the fatal day |

When no prey is visible, a predator falls back to `_choose_destination`, whose food score uses plant biomass. It has no remembered prey-location route. That fallback can keep it away from animals even while the world’s herbivore population grows. World-wide abundance is not local access.

Predator reproduction requires a consecutive support streak of 912 days at this timebase: a 90-reference-month cooldown converts to 2,738 daily ticks, and the streak must reach one third of that. A supported predator day requires fresh feeding success and visible prey. Hunt opportunities average 12 per year. A non-hungry day calls the plant-feeding function, which supplies no predator food and resets feeding success to zero, breaking the streak. The replay’s largest observed predator support streak was one day. This makes replacement effectively prohibitive under the current rules.

Animal size calibration is also much smaller than Agentus calibration: the predator target is 0.085 kg of dry tissue, versus 28 kg for an adult human. This requires an explicit calibration decision before interpreting the world as having human-scale predator pressure. Founders are about 48 at year 30; the human old-age rule is a hard 90-year limit, so no founder old-age death is due yet.

Report correction: seed a’s three captures were two grazers and one browser, not three grazers. Seed b’s two captures were one grazer and one predator.

Sources: `ecology/animals.py`, `_choose_destination`, `_consume_plants`, `evolve_consumers`; `ecology/traits.py`; `human/calibration.py`.

## 3. Child energy deaths

All 13 fatalities were under the 180-day solid-food onset, remained with a caregiver, and had no solid intake on their fatal day. Each caregiver finished that nursing allocation at the 200-kcal floor used by the child’s effective profile. The child’s energy reserve declined to exhaustion; the prior energy-store clamp is not the observed mechanism.

| Seed | Child | Generation | Year | Age at death (days) |
|---|---|---:|---:|---:|
| a | `human-b00000068` | 2 | 27 | 88 |
| b | `human-b00000017` | 1 | 5 | 44 |
| b | `human-b00000050` | 2 | 24 | 42 |
| b | `human-b00000077` | 2 | 29 | 41 |
| b | `human-b00000078` | 2 | 29 | 40 |
| d | `human-b00000025` | 1 | 5 | 33 |
| d | `human-b00000024` | 1 | 5 | 105 |
| d | `human-b00000068` | 2 | 24 | 34 |
| d | `human-b00000079` | 2 | 25 | 41 |
| d | `human-b00000078` | 2 | 25 | 42 |
| d | `human-b00000101` | 2 | 27 | 43 |
| d | `human-b00000121` | 1 | 29 | 31 |
| d | `human-b00000122` | 1 | 29 | 32 |

The three early year-5 cases provide full family milk-and-food traces:

| Seed / infant age | Infant milk that day (kcal) | Infant basal demand (kcal) | Older siblings’ milk (kcal) | Older siblings’ refused food energy (kcal) |
|---|---:|---:|---:|---:|
| b / 44 days | 115.4 | 200.0 | 724.1 | 702.4 |
| d / 33 days | 102.7 | 200.0 | 736.8 | 717.5 |
| d / 105 days | 78.1 | 200.0 | 761.4 | 770.9 |

Each early mother had five live children under five. Dependent children act in ID order: older children nurse first. Nursing refills their reserve before self-feeding or the complementary-food hunger check. Older self-feeding siblings then ingest solid food and refuse some of its energy because their stores are already full. The newest infant receives the remaining milk, cannot yet eat complementary food, and loses energy.

This is measured misallocation under the existing ordering and demand definition. It does not prove that one proposed ordering change would eliminate every death; that requires a controlled counterfactual. It does establish why aggregate biomass and adult survival alone are misleading measures of infant food security. The known adult-reference/child-reference hunger inconsistency remains separate; these fatal newborns did not plan their own foraging.

Sources: `human/biology.py`, caregiver-first/dependent-ID ordering, `_provision_dependent`, `_provision_solid_food`; `human/diet.py`, `ingest_pool`.

## 4. Social learning and the zero counter

`imitation_paid` measures positive immediate net food reward for actions tagged as explicitly imitated in that tick. Building a useful object without immediate food earns an effort cost and is counted unpaid. Later tool use credits preparation through `_credit_preparation`, which does not revisit the imitation payoff counter.

There is another observation route: `observe_outcome` uses the observer’s own appraisal to create or update affordance values. It can create an entry with `n = 0`, meaning no own trial. `choose` defines untried by absence from that dictionary, instead of zero own trials. Thus observation can exclude an act from explicit imitation before it has been tried. A fixed 400-choice micro-probe yielded 128 tagged imitation choices with no value entry, and zero after adding the zero-trial entry `{n: 0, v: 0}`.

Seed c’s final actor records show repeated tool acts by four individuals: two founders and generation-1 individuals `human-b00000008` and `human-b00000009`. Their positive learned acts include cutting wood with a small stone, binding a stone to a stick, and striking browsers with sticks or short wood. In year 25, `human-b00000008` already had positive zero-own-trial entries for cutting wood with a small stone and binding a small stone to a stick: observation-derived values existed before own trials. By year 30 the cutting entry had one own trial and a positive value of 0.06454.

Therefore “social learning never produced value” is unsupported. World-born learned tool use is present. The current evidence separates successful learning from immediate tagged-copy profit; it does not assign every useful habit to a specific teacher or imitation event.

Sources: `human/interactions.py`, `choose`, `observe_outcome`, `_own_appraisal`, `learn_from_tick`, `_credit_preparation`; seed-c year-25/year-30 cognition and `capacity_stats.exploit_agents`.

## Next implementation scope

1. Correct the nursing/solid-food allocation order and remaining-demand measurement, then compare infant outcomes under the unchanged world.
2. Correct predator support accounting for episodic meals and elapsed time. Test reproduction with reachable prey before changing prey abundance or lethal pressure.
3. Record explicit parentage and maternal/paternal ancestry; decide mating and kinship behavior separately.
4. Distinguish zero-own-trial entries from performed acts and report immediate, delayed and observation-derived learning separately.
5. Make the animal size/threat calibration explicit before increasing general mortality.

No simulation mechanics were changed in this diagnosis. Extending past year 37 can test generation-2 adulthood, but it should not substitute for correcting these interpretation and mechanism problems.
