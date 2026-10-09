# V4 discovery diagnosis — 2026-10-09

The first-year bottleneck is usable payoff and physical opportunity, not a total
absence of experimentation. Agentus spontaneously fracture stone, interlace
strands, wear surfaces and arrange wood. None of these worlds establishes a
value-driven learned sequence.

## Scope and verification

Three untrained seeds ran for 365 days in each of two configurations: V4's
existing baseline, and V4 with consequential wind plus subcell positions. No
materials, instructions, recipes, energy or rewards were injected. The two flags
are a configuration bundle; this comparison does not isolate wind's causal effect.

Each of the six observed runs has a full unobserved twin. All six ledger digests
match. Three additional wind-enabled runs measure protection from existing
material even after its originating learning trial expires; their hashes also
match the corresponding unobserved twins. These are nine successful observer
comparisons over 15 year-long executions, not 15 independent ecological seeds.

All ledgers verify. Maximum relative element error in the main census is
3.82e-15, and the three-interactions-per-agent-tick limit holds. Two diagnostic
tests pass: full-weather ledger/state parity and complete hook restoration.
Core behavior, physics, production configuration and deployment are unchanged.

Opportunities below count an action offered at least once per independent
agent-day. Attempts count actual actions; several may occur in a day. An agent-day
with an action may also contain a later decision to stop. Do not interpret the
`no_choice_with_options` counter as a whole day without action.

## First-year results

| Measure, three seeds combined | Existing V4 baseline | Wind + subcell V4 |
|---|---:|---:|
| Independent interaction agent-days | 8,760 | 8,760 |
| Days meeting energy/water sequence guards | 8,745 | 8,743 |
| Days with at least one chosen action | 783 | 735 |
| Stone-strike opportunity days | 3,983 | 3,889 |
| Stone-strike attempts | 87 | 83 |
| Fractures | 22 | 21 |
| Edged fragments introduced | 3 | 6 |
| Edged-stone pickup opportunity days | 25 | 144 |
| Edged-stone pickup attempts | 1 | 2 |
| Tool-assisted tissue-cut opportunity days | 5 | 3 |
| Tool-assisted tissue cuts | 0 | 0 |
| Interlacing opportunity days | 2,242 | 2,617 |
| Surfaces actually made | 26 | 25 |
| Wearing opportunity days | 556 | 382 |
| Actual wearing changes | 17 | 20 |
| Wood-arrangement opportunity days | 2,295 | 1,446 |
| Arrangement attempts | 25 | 26 |
| Value-driven sequence choices | 0 | 0 |

Across both configurations, reserves permit sequence selection on 17,488 of
17,520 interaction agent-days (99.82%). Urgent energy/water guards are therefore
not the main first-year barrier in these runs.

### Stone: the useful continuation is rarely available

There are 170 stone strikes and 43 fractures, so contact and physical experimentation
occur. Only three edged-stone pickups occur. Held cutting tools and fresh tissue
coincide on just eight opportunity days across all six worlds, and no tool-assisted
tissue cut is performed. The one tissue-cut attempt is bare-handed.

This is materially different from the controlled training fixture, which repeatedly
supplied blunt stones and known fresh tissue together. A longer planner cannot
collect a meal that is not physically accessible. These data identify a scarce
first-year opportunity; they do not justify seeding kills, raising reward, or
changing animal abundance. Later ecological population growth has not been sampled.

### Woven material: real discovery, negligible protection at its observed scale

Agents make 51 surfaces and wear material 37 times without supplied instructions.
The surviving surfaces cover only 0.275–6.420 cm² each. This is tiny material,
not body-scale protective coverage.

In the three wind-enabled worlds, interlacing costs 625 kcal and wearing costs
80 kcal: 705 kcal combined, excluding extraction, splitting and twisting. The
entire year's measured marginal thermal-energy saving from all existing worn
material is only 0.818884 kcal. The measured saving entering active trial readouts
is 0.054061 kcal; discounted learning credit is smaller still.

The supplementary readout uses the same actual weather, terrain, fire, position
and skin wetness. It changes only attribution references on a copied body, never
world state or reward. It measures thermal-energy savings, not avoided wetting,
injury, aesthetics or other possible uses.

There is also a delayed-credit gap: 192 of 217 beneficial worn-material agent-days
have no active wearing trial. Expiry or invalidation prevents credit then; this
census does not separate those causes. However, crediting every measured benefit
would still leave less than one kcal against 705 kcal of interlacing/wearing.
Extending memory alone cannot repair that economics.

The live surface affordances offer grasp/release/wear, but no operation that joins
existing surfaces into a larger one. Strand twisting can consolidate material,
so the observed size is not an absolute mathematical ceiling. It is the scale
these untrained agents actually achieve.

### Wood arrangements: manipulation happens without realized thermal return

Agents make 51 arrangement attempts, alongside 86 force attempts. Their combined
force/arrange effort costs 1,502.282 kcal across the six worlds. Arrangement trial
readouts are zero. The supplementary wind-enabled measurement of all existing
arrangements, including expired origins, also reports zero thermal saving.

Only 0.476 kg of arranged material remains across all six worlds at year end.
That is a final retained quantity, not a peak or total production figure.

Source inspection identifies a physical access limitation worth fixing before
adding cognition: `actions.py` places arrangement geometry at the cell centre;
`biology.py` assigns founders fixed subcell offsets and requires occupants to be
inside that geometry's footprint. The live action space has no within-cell
repositioning operation or placement/orientation choice. Ordinary grid movement
changes the cell, not that offset. Small arrangements can therefore be physically
irrelevant to their maker's position. Larger geometry could eventually reach the
offset, so this is not a proof that every possible arrangement is unusable.

Cold is present: the wind-enabled runs contain 1,127 physiological agent-days
with accumulated cold exposure, including dependents. Lack of all cold conditions
does not explain the result.

### Sequence confirmation is sparse

All six worlds finish with zero transition links observed at least twice. Only
six frontier-exploration choices occur across the six runs. Ordinary exploration,
retry or imitation accounts for the other 1,805 selected actions. No sequence
choice is recorded at any time.

The existing requirement for repeated adjacency in matching material/weather
contexts is difficult to satisfy under these sparse trials. This is evidence of
sparse confirmation, not an isolated causal test of exploration probability,
forgetting, state abstraction or link thresholds. Lowering every threshold would
risk teaching correlated or uneconomical activity.

## Next implementation boundary

Address physical work and access before expanding cognition again:

1. Give general material placement and costed local repositioning actual coordinates,
   so a maker can encounter the geometry they changed. Preserve footprint, mass,
   wind direction and transactional execution; supply no shelter goal.
2. Support general incremental joining/manipulation of existing flexible material,
   so accumulated mass can form a meaningful surface. Validate area, material loss,
   effort and cohesion together; do not inflate insulation or reward.
3. Sample later stone/food opportunities in the existing ecology before changing
   abundance. Then isolate retesting/continuity in a costed experiment if useful
   outcomes exist but are still not repeated.

The wearing-trial expiry issue deserves a separate provenance test, but it is
secondary to the measured scale/payoff gap here. Sequential imitation remains
premature until a useful independently acquired practice exists.

## Reproduction and evidence limits

```bash
PYTHONPATH=src:. python -m qualification.genesis.discovery --days 365 --output experiments/genesis/summaries/DISCOVERY_CENSUS_V4_2026-10-09.json
PYTHONPATH=src:. python -m qualification.genesis.discovery --days 365 --parallel 3 --thermal-followup experiments/genesis/summaries/DISCOVERY_CENSUS_V4_2026-10-09.json --output experiments/genesis/summaries/THERMAL_EXPOSURE_V4_2026-10-09.json
PYTHONPATH=src:. python -m pytest -q tests/genesis/test_discovery_census.py
```

Machine-readable counts, costs, quarterly opportunities, rewards, configuration
fingerprints and ledger hashes accompany this report in those two JSON files.
The read-only diagnostic is `qualification/genesis/discovery.py`.

This is three seeds in the first year, not a long-run survival or cultural
transmission test. Failure to discover a useful sequence here does not establish
impossibility in later ecology or another physical configuration. No production
behavior or deployment has been changed.
