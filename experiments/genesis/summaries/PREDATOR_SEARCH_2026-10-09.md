# Predator search and encounter memory — 2026-10-09

`seen-prey-v1` removes plant-abundance steering from predator movement. A hungry predator follows actually visible live prey; a sated predator stays in a patch where it can see prey. If no prey is visible it revisits remembered encounter locations or explores adjacent cells. Movement still pays the existing cost and requires the existing elapsed-time opportunity.

## Information and movement contract

Only live herbivores within the species' existing perception radius enter encounter memory. Already-killed prey is excluded. Memory stores the observed coordinate and observation epoch, not a live prey pointer, inferred destination, off-screen tracking or inherited knowledge. Visible empty patches invalidate memories immediately. The remembered location can be approached beyond current sight, but its prey is not assumed still present.

The declared experimental limits are one calendar year of encounter retention, at most 16 remembered prey cells and 32 remembered cells actually occupied by the predator. These are bounded behavioral assumptions, not empirically calibrated stalker cognition. Memory lifespan scales to 12 monthly or 365 daily ticks. Oldest records are evicted first.

Visible actual water has priority when reserves are below half capacity. Otherwise visible prey comes first, then the nearest remembered encounter (freshness resolves distance ties). Without prey information, cardinal neighboring cells are explored in order of least recent actual visit, with deterministic agent/epoch tie-breaking. The choice grants no extra movement opportunity and acquires no food. Successful hunting still requires the original local encounter, opportunity draw and hunt-success rule.

Sated animals staying in a visible prey patch and the visited-cell exploration rule are explicit policy choices. They are not learned or shown to be optimal. Cached locations and visits start empty in offspring. Herbivore movement and the earlier predator support, nursing, metabolic and reproduction parameters are unchanged.

The default remains `plant-score-legacy`. Existing states without the new search key retain their earlier behavior. `predator_search_model="seen-prey-v1"` receives a distinct fingerprint/state key. Observer/replay arm: `v1-remainingmilk-reservepredators-searchpredators`. Baseline arm: `v1-remainingmilk-reservepredators`.

## Ten-year comparison

Four unchanged seeds run for ten years from initial state. The reference holds the nursing and reserve-support corrections active and leaves predator search on the old plant-scoring rule. Reference annual records come from the preceding verified replay; search-arm replays use the same canonical scheduler and have distinct fingerprints.

| Seed | Reference predators alive | Search predators alive | Search generations 0 / 1 / 2 | Human alive / births / deaths in both arms | Reference → search other animals |
|---|---:|---:|---|---|---|
| a | 0 | 3 | 1 / 1 / 1 | 21 / 13 / 0 | Browsers 8 → 3 |
| b | 0 | 0 | 0 / 0 / 0 | 29 / 21 / 0 | Browsers 16 → 16; grazers 16 → 16 |
| c | 1 | 3 | 1 / 1 / 1 | 18 / 10 / 0 | Browsers 8 → 8; grazers 8 → 4 |
| d | 0 | 0 | 0 / 0 / 0 | 48 / 40 / 0 | Browsers 12 → 12 |

Predator births are directly recorded, not inferred from annual abundance:

| Seed | Parent generation | Child generation | Epoch | Year |
|---|---:|---:|---:|---:|
| a | 0 | 1 | 1362 | 4 |
| a | 1 | 2 | 3187 | 9 |
| c | 0 | 1 | 1818 | 5 |
| c | 1 | 2 | 3643 | 10 |

All four descendants remain alive at year ten. B is still captured on day 17. D starves at epoch 385 (year 2), earlier than epoch 687 in the reference: exploration pays additional actual movement costs without finding prey. B and D still lose their founders before replacement; the search correction does not guarantee a successful predator lineage. The final human totals match, but intermediate histories can differ, and final prey populations change. This is evidence of a causal movement/encounter effect under the existing stylized animal biology, not a claim of realistic predator sizes or calibrated human danger.

The single search policy was tested on all four seeds without adjusting movement chances, hunt success, energy, reproduction duration or prey abundance to obtain these outcomes. The saved evidence includes each birth event, annual visibility/support observations and every final predator's state, including its bounded encounter and visit memories.

## Validation

- Twelve new search regressions pass: actual visible prey, sated patch retention, hidden-prey/plant isolation, stale and expired memory, dead/killed prey, local water, bounded movement and costs, opportunity gating, bounded exploration, non-inherited memory, and deterministic fingerprints.
- Three-seed × 75-day combined-arm smoke: zero failures/warnings; valid ledgers, observed/unobserved digest equality and maximum relative element balance error approximately 1e-15.
- Complete 30-day canonical scheduler-state parity passes before and after instrumentation for each of four new search runs. Long-run production ledger digests are not reconstructed.
- With search absent, the revised consumer kernel matches the preceding kernel on every complete consumer/producer/matter state over four years at both monthly and daily time steps (48 + 1,460 steps).
- A real four-year controlled search/reproduction run conserves elements within 4.0e-7 kg and water within 5.7e-7 kg and ends with a living predator offspring.
- Full suite: 356 tests pass, zero errors, failures or skips in 235.815 seconds. Completion is verified from the saved JUnit report; individual case records are included in the evidence JSON.

## Reproduce

```sh
python -m pytest tests/genesis/test_predator_search.py
python -m qualification.genesis.tiers smoke --arm v1-remainingmilk-reservepredators-searchpredators
python experiments/genesis/run_generations_diagnosis.py --seed c --arm v1-remainingmilk-reservepredators-searchpredators --years 10 --owned-state --spatial-index --out runs/predator-search
```

Repeat for seeds a, b, c and d. The diagnostic records every predator birth event and live-prey visibility days, and saves the final private replay state. Existing diagnostic callbacks are read-only and canonical scheduler-state parity is checked before and after instrumentation. Production Railway settings, default models and original checkpoints are unchanged.
