# Experienced physical transitions — stage 1

## Scope and authorization

Owner authorized starting the transition-learning extension on 2026-10-09.
This resumes this bounded cognition work despite the older roadmap pause.
Base: `codex/30-year-diagnosis` at `500be5c`, after PR #39 merged there.
No AGENTS.md exists in the checked-out repository.

This stage records an individual's physical experience. It does not yet value
sequences, continue a plan across ticks, change exploration, or imitate sequences.
No result here demonstrates autonomous invention of a shelter or woven protection.

## Risks assessed before editing

- Unbounded state/action combinations: explicit record, form and action limits.
- Hidden-state leakage: project own-held/worn and unheld local material only.
- Premature behavioral changes: no choice/planning reader in stage 1.
- Duplicate or spurious reward: no reward or delayed credit added in this stage.
- Checkpoint divergence: opt-in version in the config fingerprint, persisted
  cognition under the existing human authority and replay transaction.

Production changes are confined to `config.py`, `runner.py`,
`human/interactions.py`, and new `human/transitions.py`. Physical execution,
Stage-1 coordination, destination planning, deployment settings, ports and
runtime environment handling are unchanged.

## Configuration and compatibility

`GenesisConfig.agentus_transition_model` accepts:

- `none` (default): no recording, no extra human-state or cognition fields,
  and no additional canonical configuration key.
- `experienced-transitions-v1`: requires Agentus capacities, which already
  require calibrated human actions at 365 ticks/year. It persists the version
  in the configuration fingerprint and human authority state.

Example for a controlled run from the existing production configuration:

```python
from dataclasses import replace
from hrm_genesis import GenesisSimulation
from qualification.genesis.tier_observer import build_config

config = replace(build_config("agentus-demography-a", "v1"),
                 agentus_transition_model="experienced-transitions-v1")
sim = GenesisSimulation(config)
sim.run(75)
```

No experiment arm, production default or Railway service was changed. Existing
checkpoints keep their old configuration. Enabling the model on an old checkpoint
is intentionally rejected by the existing fingerprint check; this is not an
implicit migration. Newborns start without their parent's transition memory.

## Perceptual state

Before and after each real `interactions.execute` attempt, recording projects:

- held, worn and local ground object classes, approximate mass, length, area,
  cohesion and wetness;
- local plant, woody, loose, arranged, seed and carcass quantity bands;
- arrangement span, height, area, density and orientation;
- own position within the cell;
- local temperature, precipitation, wind speed/direction and own skin wetness;
- distinct currently available interaction keys from existing physical guards.

Class/quantity cues follow the existing capacity model's declared assumption
that local material properties are perceptible. These are simulation abstractions,
not a calibrated human sensory model. No elemental identities, nutritional
truth, distant material, another person's held inventory, object history, actor
intent, reward or observer classification enters the projection. Available acts
are possibilities, not goals or benefits.

Natural and picked-up stones have the same perceptual form representation.
Object identities and absolute cell coordinates are omitted so familiar physical
situations can be recognized in another place or with equivalent objects.

## Memory contract

Each edge stores before-state, interaction key, after-state, experience count,
mean actual effort in kcal, mean experienced injury, last epoch, and sets of
newly available/unavailable action keys. Separate outcomes for a matching
before-state/action retain separate counts. The state snapshots are copied,
so later material mutation cannot rewrite an earlier experience.

Declared limits:

| Quantity | Limit |
| --- | --- |
| Distinct transition outcomes per individual | 64 |
| Recent transition references | 8 |
| Distinct forms in each held/ground/worn projection | 24 |
| Identical form count represented | 3 (saturated) |
| Distinct available act keys in a projection | 64 |
| Retention since last experience | 96 daily ticks |

Re-experiencing an edge refreshes recency and updates count/cost. Least recently
experienced edges are evicted first, with insertion order breaking same-tick
ties. References to evicted or expired edges are removed. Idle interaction ticks
also prune expired memory. The normal three-interactions-per-tick limit remains.

State abstraction is intentionally lossy. Quantity bins, count saturation and
sorted truncation can hide physical differences. A recorded newly available act
means it followed an interaction under these local conditions; it is not proof
of a necessary causal dependency or guaranteed success. Planning must always
recheck live physical affordances when it is introduced.

## Verification

Executed locally on 2026-10-09:

- New transition micro contracts: **10 passed**. They cover real grasp/release,
  bulk force/arrangement, wearing, local-only perception, identity-independent
  recognition, failed attempts, alternative outcomes/costs, bounded retention,
  and opt-in/legacy fingerprints.
- `python -m pytest -q tests/genesis/micro/test_micro_transitions.py
  tests/genesis/micro/test_micro_learning.py tests/genesis/test_transition_memory.py`:
  **21 passed** (10 new micro, 7 existing learning, 4 integration).
- Integration: **3 seeds x 75 days**, model on/off. At **every tick**, all existing
  human fields match after removing only the new model tag/memory; World,
  Matter, producer Ecology and consumer Ecology match exactly. Recorded memories
  are nonempty and bounded; both arms' ledger chains validate. On/off ledger
  digests intentionally differ because configuration and new cognition differ.
- Weather and subcell-position enabled: **40 days**, uninterrupted versus
  **17 + checkpoint + 23 days**. Restored memory matches the saved memory;
  final snapshots, ledger digest and human state match exactly. Restoring under
  model `none` is rejected by fingerprint.
- `PYTHONPATH=src:. python -m qualification.genesis.tiers fast`:
  **136 micro tests passed**, followed by **3 seeds x 75 days smoke PASS**,
  **0 failures, 0 warnings**. The observed/unobserved reference rerun has identical
  ledger digests; maximum relative element balance error is **1.1e-15**.
- Additional existing integration/cognition/material/learning and joint
  cover/woven/thermal/novelty regression files: **42 passed**.
- Total distinct tests across these selections: **182 passed**.
- `git diff --check`: passed.

These verify the recording contract, compatibility and replay. The full
repository suite and long-term survival/invention experiments were not run.
No autonomous sequence use or invention is claimed.

## Next stage

Sequence valuation must learn from realized bodily consequences with explicit
credit provenance and uncertainty. Existing flat eligibility credit is not
sufficient proof of causality. Before influencing choices, add a controlled
preparation-to-benefit comparison, an unrelated-action/no-benefit control,
extinction after failure, and urgent-needs/physical-access checks. Only then
allow short learned plans and revalidated continuation across ticks. Sequential
imitation remains later and may use only actually witnessed acts/consequences.
