# Incremental interlacing — 2026-10-09

**Incremental surface work is implemented and physically qualified. Sustained useful practice has not emerged.** Untrained worlds executed one successful extension attempt across three years of aggregate observation. The separately controlled wood runs could not accumulate 30 kg in a single cell over 120 days under normal live conditions.

## Implemented physical access

The opt-in `agentus_surface_work_enabled` exposes two new interactions. An Agentus can interlace two or four currently held strands into an existing held unworn surface. It can also remove its own worn surface to the ground, then reacquire it through ordinary grasping. Neither action is a prescribed sequence or shelter/clothing goal.

Every extension attempt pays the existing 25 kcal interlacing cost scaled to development. Removal costs 4 kcal scaled to development. The six-soft-object limit, carrying mass, ownership, worn status and duplicate IDs are checked during physical execution. Successful extension consumes exact inputs and retains every constituent. Failed work costs effort but preserves inputs. Existing area loss, current cohesion and wetness are retained; short added strands may reduce span. No insulating coefficient or physiological benefit is increased.

The version defaults off. Configuration fingerprints and persisted state distinguish it from prior runs. Planning priorities, environment/deployment settings and existing cognition/history bounds remain. Contract: `docs/architecture/INCREMENTAL_INTERLACING.md`.

## Untrained ecological result

Three original ecological seeds, 365 days each, V4 memory, wind, local placement and incremental surface work. No objects, reserves, sequences or demonstrations were planted in these worlds. Three corresponding opt-out worlds were rerun and matched the preceding local-work census exactly in fingerprints and ledger digests.

| Seed | Extension opportunity agent-days | Extension attempts | Worn-surface removals | Largest surviving surface, cm² |
| --- | ---: | ---: | ---: | ---: |
| agentus-demography-a | 35 | 0 | 8 | 3.570263 |
| agentus-demography-b | 10 | 1 | 7 | 3.196058 |
| agentus-g10-4-01 | 0 | 0 | 5 | 4.604653 |

The single extension attempt in seed b changed physical material and cost 25 kcal. It was exploratory, not selected as a valued sequence. No sequence-value choices occurred in any seed, and final memory contained zero twice-observed links. The ecological largest surfaces remain only a few square centimetres. Controlled growth beyond 100 strands is a capability result, not the observed behavior of these worlds.

Interlacing, including extension, plus wearing cost 738 kcal; removals cost another 80 kcal, excluding fibre preparation. Total all-worn thermal saving was 0.3013183619 kcal, down from 0.8136919237 kcal in the preceding local-work worlds. Actors explored removing their small surfaces; useful repeat wearing or extension did not replace that behavior. The bundled opt-in comparison changes action opportunities and does not isolate the contribution of removal from extension or altered exploration choices. It demonstrates no improvement in protective behavior.

Arrangement thermal saving remained negligible: 0.0004824109 kcal total. These are actual marginal thermal-energy readouts over the year, including material outside an active learning trial. Avoided wetting, injury and other uses are not fully measured by that energy readout. The active populations finished at 11, 10 and 10, with 3, 2 and 2 births respectively.

## Controlled wood accumulation under normal ticks

A separate controller chose physical work for one founder in each of three 120-day worlds: prepare local wood toward 30 kg, then arrange it if actually possible. The controller respected existing affordances, discretionary energy/water checks and the normal action/fatigue budget. Normal movement, ecology, weather, feeding, physiology and transactions continued. No material, energy, hydration or location was injected or frozen.

These controller choices are diagnostic interventions, not autonomous Agentus behavior, learned planning, or cultural discovery. Other individuals used their ordinary policies. The experiment tests whether the favourable single-cell material envelope survives live conditions; it does not force completion.

| Seed | Controlled force selections | Controlled arrangement selections | Peak loose kg in any cell | Actor cells visited |
| --- | ---: | ---: | ---: | ---: |
| agentus-demography-a | 117 | 0 | 6.750000 | 6 |
| agentus-demography-b | 60 | 0 | 3.025252 | 21 |
| agentus-g10-4-01 | 98 | 0 | 3.977685 | 16 |

No controlled actor reached a 30 kg arrangement. Peak arranged mass across all cells was approximately 0.25 kg, including actions by uncontrolled individuals. Prepared material was distributed or altered across the live world, while the actor moved among cells and faced real resource/action constraints. This result does not isolate movement as the sole cause. It rules out treating the earlier 121-action, 1,658-kcal static envelope as a demonstrated normal-world construction route.

## Validation

- All 224 selected regression tests passed, including 12 focused incremental-interlacing/integration cases and a controller restoration/budget check.
- A controlled live-material test grew one surface beyond 100 strands over successive actions with at most five hand objects, conserved all elements, preserved histories, and paid all 600 kcal for 24 extension actions. Its newly supplied strands are test fixtures, not ecological discovery.
- Full 35-day observed opt-in execution exactly matched unobserved checkpoint restoration across every authority snapshot and ledger digest. Incompatible-version restoration was rejected.
- Three-seed 30-day production-arm smoke passed with zero failures/warnings and identical observed/unobserved ledger hashes.
- All six year-long executions and three controlled 120-day worlds passed ledger/conservation checks. Active untrained worlds retained at most three interactions per agent-tick. Maximum relative element error in active untrained worlds was 2.61e-15, and maximum absolute lithic error was 2.27e-13 kg.
- All three opt-out year-long fingerprints and ledger hashes match PR #46's stored active worlds. Those prior worlds had local work enabled and surface work absent.
- `git diff --check` passed.

## Next boundary

Test continuity of access and investment across ordinary ticks: whether an actor can recognize its own perceptible accumulated material, return to it, and repeat physically useful work without a supplied recipe or forced construction goal. Keep the real material/work economics in that qualification. The new primitive closes an access gap; it does not justify larger rewards or a claim that culture has begun.

## Reproduce

```bash
PYTHONPATH=src:. python -m pytest -q tests/genesis/micro/test_micro_incremental_interlace.py tests/genesis/test_incremental_interlace_integration.py tests/genesis/test_surface_work_gate.py
PYTHONPATH=src:. python -m qualification.genesis.smoke --days 30
PYTHONPATH=src:. python -m qualification.genesis.run_surface_work_gate --output experiments/genesis/summaries/INCREMENTAL_INTERLACE_GATE_2026-10-09.json
```

Raw current data, including controlled trajectories, are in `INCREMENTAL_INTERLACE_GATE_2026-10-09.json`. The gate reuses the previous `LOCAL_WORK_GATE_2026-10-09.json` only for historical digest comparison. Nothing was merged or deployed during this step.
