# Local material work v1

The discovery census found that Agentus could make arrangements but could not change their within-cell position. Small arrangements remained centred on the cell, often away from their makers. Woven surfaces could be made and worn but could not be joined. This opt-in extension exposes physical operations through the existing affordance, execution, physiology and transactional paths.

## Version boundary

`GenesisConfig.agentus_local_work_enabled` defaults to false. It requires `agentus_subcell_position_enabled`, which already requires capacities. The active configuration fingerprint includes `agentus_local_work: local-material-v1`; initial human state records the same version. Earlier configurations omit that key. Checkpoint restoration uses persisted state and rejects incompatible fingerprints.

No production runner defaults, environment variables, deployment settings or biological priority rules change. Planning receives no named shelter, clothing, recipe, target utility or prescribed sequence.

## Physical operations and declared assumptions

| Operation | Physical constraint | Work |
| --- | --- | --- |
| Local movement | Four cardinal 0.25 m steps; both coordinates remain in the existing 2 m local window, from -1 to +1 m. Grid cell does not change. | `(2 + distance × (2 + 0.25 × carried kg)) × development scale` kcal. |
| First bulk arrangement | Uses maker's actual local coordinates. Existing mass and geometry constraints remain. | Existing arrangement cost. |
| Adding/removing bulk material | Arrangement centre remains fixed. Centre must be within 1 m of the actor. | Existing material manipulation costs. |
| Rotation | Existing arrangement within 1 m; quarter turns, without changing mass, area or centre. | `(4 + 2 × arranged kg) × development scale` kcal. |
| Joining surfaces | Two held, unworn surfaces and one held strand. Approximate square patches; strand length at least twice the shorter edge, flexibility at least 0.5, friction at least 0.3, tensile strength sufficient to bear total weight, resulting cohesion at least 0.5. | `(8 + 20 × shorter edge in m) × development scale` kcal, including failed physical attempts. |

The existing minimum effort floor, fatigue increment, carrying constraints, and three interactions per tick remain. A newly remembered action cannot bypass current affordance checks or physical execution.

The first arrangement stores `center_offset_m` in its geometry. Later additions do not reposition it. Protection checks occupancy relative to that centre; arrangements lacking the field retain the historical cell-centred interpretation. Orientation keeps the existing coarse incident-wind calculation. Rotating the face does not introduce a new airflow solver or change the existing footprint model.

A successful join consumes both surfaces and the entire strand. The resulting surface contains all their constituent strands exactly once. Area is the sum of input areas minus 10% of the smaller area for overlap; the binder adds no coverage. Cohesion cannot exceed the weaker patch and falls with binder friction and integrity. Failed joins leave their inputs intact. Existing surface decay, element accounting, history propagation, release, carrying and wearing operate on the resulting surface. No material or thermal reward is created by joining.

## Perception and learning

Active transition perception adds coarse arrangement-centre coordinates to existing perceptible geometry. Exact elemental composition and attribution provenance stay outside cognition.

In delayed transition modes (V3/V4), arranging, rotating, or moving locally can initiate the existing arrangement trial when physical placement actually changes. Its reference contains the previous arrangement and previous occupant offset. Physiology computes marginal thermal energy savings under current weather, terrain, fire and actual skin wetness. The world uses only the actual new state. The reference affects measurement, not physics.

Multiple qualifying actions share one measured arrangement benefit. Worn and arrangement contributions retain the existing joint benefit budget. Trials remain bounded to two kinds and expire under the existing horizon; subsequent movement, arrangement revision, leaving the cell, or loss of originating memory invalidates the arrangement trial. Same-epoch settlement is idempotent. V2 retains its existing first-tick credit interface; the extended delayed placement attribution is qualified in V4.

## Limits

This is still one bulk arrangement per cell. Adding material at another point cannot silently move an existing arrangement. Independent structures, translation of an existing structure, precise loose-object coordinates and world-wide body-scale reach are outside this change. Loose pools retain the previous cell-local access abstraction. The local window is an explicit assumption, not a newly inferred world cell size.

Joining permits material accumulation but does not make thin patches economical. The existing mass-to-area constraints, raw fibre extraction, work budgets and physiology remain. No claim of emergent shelter, clothing, sustained practice or cultural inheritance follows from enabling these operations.

## Qualification

Micro tests exercise placement at the maker, fixed centres on addition, bounded costed movement, unreachable material rejection, rotation, measured occupancy credit and its invalidation, failed seams, conserved live joins, existing decay, and opt-out affordances. Integration tests compare full observed execution with checkpoint restoration, all authority snapshots and ledger hashes, test observer neutrality and action limits, and reject incompatible restores.

`qualification.genesis.run_local_work_gate` runs three untrained 365-day V4 worlds with wind, subcell position and local work active. It also reruns the three corresponding opt-out worlds and compares their fingerprints and ledger digests with the recorded parent-branch census. This separates physical validity and historical compatibility from any claim about spontaneous discovery.
