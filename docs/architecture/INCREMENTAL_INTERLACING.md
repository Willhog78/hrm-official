# Incremental interlacing v1

The material-scale diagnosis found that live initial interlacing consumes only currently held raw strands. Existing material geometry supports larger strand sets, but there was no physical operation for adding strands to a surface across successive actions. Worn surfaces were also inaccessible to further manipulation.

## Version and ownership

`agentus_surface_work_enabled` defaults to false and requires Agentus capacities. Active configuration fingerprints include `agentus_surface_work: incremental-interlace-v1`; human state persists `surface_work_model` with that value. Earlier configurations omit the key and retain their behavior. Checkpoint restoration validates the fingerprint and restores persisted objects and cognition.

Matter computes the resulting physical surface. Human interactions enumerate and execute physically accessible actions, pay costs, and learn through existing experience paths. The existing multi-authority transaction and replay system commits the material/body changes. No planner priorities, physiological coefficients, environmental defaults or deployment settings change.

## Actions

`interlace:surface+strands|held` requires one held unworn surface and at least two held raw strands. It adds two or four strands, selecting the longest available raw strands with stable ID tie-breaking. Both affordance enumeration and execution retain the six-soft-object hand limit and development-scaled carrying limit. Execution rechecks ownership, worn status, material type, distinct input IDs and the current version.

Each valid interlacing attempt costs the existing 25 kcal multiplied by development scale. The normal minimum effort, fatigue increment, reserve-dependent choice and three-interactions-per-tick limit remain. Failed physical work consumes effort but retains its input objects.

`release:surface|worn` removes an own worn surface and puts it on the ground, costing 4 kcal multiplied by development scale. It does not put material into an already full hand. Reacquisition uses the existing grasp affordance and its normal capacity checks. Removing another actor's material fails. There is no automatic removal or reworking plan.

## Material geometry and damage

Successful extension consumes the existing surface and added strands, producing one held unworn surface containing every original constituent exactly once. No matter is gained or discarded. Existing object history propagation merges the consumed inputs' preparation histories; existing decay and wearing operate on the result.

Geometry uses the same `interlace` calculation as initial surface formation. Let `A_old_nominal` be its calculation on the existing constituent strands and `A_old_actual` the current stored surface area. The retained fraction is `min(1, max(0, A_old_actual) / A_old_nominal)`. The new nominal area on all constituents is multiplied by that fraction. Zero old nominal area fails. This preserves an existing area deficit rather than treating reworking as a fresh pristine surface. Reworking a joined surface can change its layout and reduce its area.

Resulting cohesion is the smaller of the existing surface's current cohesion and the new strands' combined material calculation. It cannot heal old degradation. Current wetness is at least the maximum of old surface wetness and added-strand wetness. Zero resulting area or cohesion below 0.5 fails intact. Short strands can reduce the resulting span; adding material does not guarantee benefit.

This remains the existing coarse strand geometry and thermal-coverage model. The change provides incremental physical access; it does not validate those models against real-world textile manufacturing or introduce a coverage multiplier.

## Learning

The normal transition recorder sees actual changed held forms, material and new affordances. Only later experienced consequences can value preparation. Existing food and delayed thermal attribution, bounded history, transition memory, physiological reserve guards and same-epoch benefit settlement remain.

No stored sequence, semantic skill descriptor, shelter/clothing objective, inherited reward or scripted action chain is inserted. Untrained ecological runs determine whether actors use the new operation. Controlled physical examples establish capability only.

## Qualification

Micro tests grow a surface beyond 100 constituent strands through successive costed live actions while using at most five hand objects, check material conservation and preparation history, preserve area/cohesion/wetness deficits, reject remote/worn/duplicate/over-capacity inputs, charge failed work, and verify removal followed by normal reacquisition. Integration checks version isolation and complete observed/unobserved checkpoint replay.

`run_surface_work_gate` executes three untrained 365-day worlds with wind, local work, V4 memory and surface work. It reruns the three corresponding opt-out worlds against PR #46's captured fingerprints and ledger hashes. Thermal probes are read-only and action counts distinguish offered interactions from actual attempts.

The same gate also runs three separately labelled 120-day wood fixtures with controlled action selection. A controller asks one founder to prepare local wood toward 30 kg while respecting the actual options, existing fatigue/action limits and discretionary reserve conditions. Normal ecology, weather, movement, physiology, food and transactions continue; no material or reserves are planted. These runs qualify accumulation under normal ticks. Their controller choices are not autonomous discovery or learned construction evidence, and they are never installed in production.

Constituent object data grows with actual accumulated strands, as in existing surface joining. Cognition/history bounds remain. Long-run manufacturing performance and profitable ecological repetition remain separate qualification questions.
