# Local material work — 2026-10-09

**Physical placement is now usable. Useful discovery has not emerged in the three year-long runs.** Opt-in Agentus can step within their cell, arrange material at their actual position, rotate reachable arrangements, and join two held surfaces with a real strand. The existing planners, biological priorities and material-to-protection calculations remain.

## Ecological result

Three independent seeds, 365 days each, V4 transition learning with wind and subcell positions. No objects, recipes, rewards, demonstration sequences or extra reserves were planted. These are the same ecological seeds as the diagnosis, not independent new-world replication.

| Seed | Local moves | Rotations | Surfaces made | Wear changes | All arrangement thermal saving, kcal | All worn thermal saving, kcal |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agentus-demography-a | 61 | 5 | 9 | 8 | 0.0000000000 | 0.1556739783 |
| agentus-demography-b | 58 | 8 | 9 | 7 | 0.0000000772 | 0.1929365978 |
| agentus-g10-4-01 | 64 | 10 | 9 | 5 | 0.0002502680 | 0.4650813476 |

Across these worlds, Agentus made 183 local moves, 23 rotations, 26 arrangement attempts, 27 surfaces and 20 wear changes. Total measured arrangement thermal saving was 0.0002503452 kcal; the parent worlds measured zero. This demonstrates a physically reachable effect, not economical protection. Only two arrangement-related thermal credit readouts occurred, both from actual arranging.

Interlacing and wearing cost 755 kcal, excluding fibre preparation. All worn material saved 0.8136919237 kcal. This remains the same basic scale problem as the diagnosis. Surviving surfaces were at most 4.604653 square centimetres individually. Joining does not create coverage beyond its input patches.

No agent-day offered the complete joining combination (two held unworn surfaces and a held strand), so no join was attempted in these untrained runs. The live joining path passes controlled physical tests; ecological acquisition remains unproven. There were zero sequence-value choices and zero twice-observed links in final memory. The new affordances also change the mix of exploration opportunities, so differences cannot be attributed to placement alone.

Cold exposure occurred on 1,066 physiological agent-days, including dependents. The readout measures marginal thermal energy savings at actual weather, fire, terrain and skin wetness. It does not measure avoided wetting, injury or all possible material uses. Active runs finished with 11, 10 and 10 living Agentus and 3, 2 and 2 births respectively.

## Validation

- The regression selection passed all 206 tests. Twelve local-work micro tests passed after adding two extra rotation/failure cases; ten overlap that selection, for 208 distinct tested cases.
- Full 35-day opt-in simulation with thermal observation exactly matched checkpoint restoration without the observer: all authority snapshots, human state and ledger digest. Chain verification and three-actions-per-agent-tick limit passed. Incompatible configuration restoration was rejected.
- Three opt-out 365-day worlds reproduced the recorded parent census fingerprints and ledger digests exactly. This checks historical behavior, not merely configuration equality.
- All six year-long worlds passed ledger-chain and conservation checks. Maximum relative element error in the three active worlds was 2.84e-15; maximum absolute lithic error was 2.27e-13 kg. At most three physical interactions occurred per agent-tick.
- Three-seed, 30-day production-arm smoke passed with zero failures and zero warnings. Its observed/unobserved ledger comparison matched.
- `git diff --check` passed.

## Scope and assumptions

The version is `local-material-v1`, controlled by `agentus_local_work_enabled=False` by default. Production configuration and deployment settings were not changed. The exact geometric and work assumptions are documented in `docs/architecture/LOCAL_MATERIAL_WORK.md`.

The existing one-arrangement-per-cell representation remains. The first arrangement follows its maker; additions preserve its centre and must be within one metre. Local cardinal steps are 0.25 m within the existing two-metre window. Arrangements lacking centre coordinates retain their legacy interpretation. No independent second arrangement, wholesale structure translation, or precise loose-object coordinate system is added.

Surface joining uses a coarse seam model with actual held inputs, seam length, flexibility, friction, integrity and tensile strength. Success consumes both patches and the entire binder, preserving all elements. Ten percent overlap reduces combined area. Failed joins cost effort and leave inputs intact. Joined surfaces use existing degradation, wearing, material accounting and history mechanisms.

Delayed V3/V4 thermal attribution now includes the previous occupant position. It compares real physical contributions, divides the existing benefit budget across originating actions, settles once per epoch and invalidates after physical changes. It adds no predicted reward or protected state.

## Next boundary

Measure whether generic material work can produce consequential physical coverage at credible effort before adding more memory or imitation. Separate the two present barriers: raw patch scale and obtaining two unworn patches plus a binder. Use controlled material-response measurements to examine the model, followed by untrained ecological verification. Do not raise rewards, plant recipes, or interpret a nonzero decimal as successful shelter discovery.

## Reproduce

```bash
PYTHONPATH=src:. python -m pytest -q tests/genesis/micro/test_micro_local_work.py tests/genesis/test_local_work_integration.py
PYTHONPATH=src:. python -m qualification.genesis.smoke --days 30
PYTHONPATH=src:. python -m qualification.genesis.run_local_work_gate --output experiments/genesis/summaries/LOCAL_WORK_GATE_2026-10-09.json
```

The gate reuses `DISCOVERY_CENSUS_V4_2026-10-09.json` only as a historical opt-out digest baseline. It runs all six current worlds afresh. The raw current evidence is in `LOCAL_WORK_GATE_2026-10-09.json`.
