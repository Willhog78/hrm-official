# HRM Predetermined File Tree

This tree is the target structure for the Genesis vertical slice.

Existing Stage-1 files remain in place. New implementation should conform to this layout unless a documented architecture decision explicitly changes it.

```text
hrm-official/
├── README.md
├── STATUS.md
├── ROADMAP.md
├── FILE_TREE.md
├── pyproject.toml
│
├── docs/
│   ├── HRM_MASTER_DEVELOPMENT_PLAN_v1.1.md
│   ├── architecture/
│   │   ├── GENESIS_CAUSAL_CONTRACT.md
│   │   ├── WORLD_STATE_OWNERSHIP.md
│   │   ├── G10_1_SCALE_SUBSTRATE.md
│   │   ├── G10_2_HUMAN_CALIBRATION.md
│   │   ├── G10_2A_SURVIVAL_AFFORDANCES.md
│   │   └── ADR/
│   └── stage0/
│
├── src/
│   ├── hrm_coordination/          # existing Stage-1 foundation
│   │   ├── authority.py
│   │   ├── checkpoint.py
│   │   ├── fabric.py
│   │   ├── ledger.py
│   │   ├── model.py
│   │   ├── seeds.py
│   │   └── temporal.py
│   │
│   └── hrm_genesis/
│       ├── __init__.py
│       ├── config.py
│       ├── runner.py
│       ├── checkpoint.py
│       │
│       ├── world/
│       │   ├── grid.py
│       │   ├── terrain.py
│       │   ├── climate.py
│       │   ├── water.py
│       │   ├── soil.py
│       │   └── energy.py
│       │
│       ├── matter/
│       │   ├── __init__.py
│       │   ├── elements.py
│       │   ├── pools.py
│       │   ├── transfers.py
│       │   └── accounting.py
│       │
│       ├── ecology/
│       │   ├── plants.py
│       │   ├── decomposition.py
│       │   ├── animals.py
│       │   ├── populations.py
│       │   └── traits.py
│       │
│       ├── human/
│       │   ├── biology.py
│       │   ├── perception.py
│       │   ├── memory.py
│       │   ├── learning.py
│       │   ├── planning.py
│       │   ├── actions.py
│       │   └── communication.py
│       │
│       ├── observer/
│       │   ├── metrics.py
│       │   ├── ecology.py
│       │   ├── population.py
│       │   └── emergence.py
│       │
│       └── interfaces/
│           ├── authorities.py
│           ├── events.py
│           └── snapshots.py
│
├── tests/
│   ├── test_stage1_coordination.py
│   ├── test_stage1_hmt_contract.py
│   │
│   └── genesis/
│       ├── test_g0_integration.py
│       ├── test_g1_physical_world.py
│       ├── test_g1_5_matter.py
│       ├── test_g2_plants.py
│       ├── test_g3_consumers.py
│       ├── test_g4_ecological_loop.py
│       ├── test_g5_human_biology.py
│       ├── test_g6_cognition.py
│       ├── test_g7_actions_learning.py
│       ├── test_g8_multi_population.py
│       └── test_g9_observer_isolation.py
│
├── qualification/
│   ├── hmt_stage1_gate.py
│   ├── reproduce_stage1.py
│   └── genesis/
│       ├── run_g0_gate.py
│       ├── run_g1_gate.py
│       ├── run_g1_5_gate.py
│       ├── run_g2_gate.py
│       ├── run_g3_gate.py
│       ├── run_g4_autonomy_gate.py
│       ├── run_g7_emergence_gate.py
│       ├── run_g8_multi_population_gate.py
│       ├── run_g9_observer_gate.py
│       ├── run_g10_1_scale_gate.py
│       ├── run_g10_2_human_calibration_gate.py
│       ├── run_g10_2a_survival_affordance_gate.py
│       └── scenarios/
│
├── experiments/
│   └── genesis/
│       ├── configs/
│       ├── runs/
│       └── summaries/
│
├── evidence/
│   ├── stage1/
│   └── genesis/
│       ├── G0/
│       ├── G1/
│       ├── G2/
│       ├── G3/
│       ├── G4/
│       ├── G5/
│       ├── G6/
│       ├── G7/
│       ├── G8/
│       └── G9/
│
├── governance/
├── reviews/
├── journals/
├── drafts/
└── stage1/
```

## Ownership rules

- `hrm_coordination` coordinates; it does not own world state.
- `world` owns environmental state.
- `matter` owns conserved/transferred material pools.
- `ecology` owns organism/population state.
- `human` owns human body/cognition state.
- `observer` owns measurements only and cannot mutate causal state.
- Cross-domain changes occur through declared interfaces and Stage-1 transactions.

## Dependency direction

```text
coordination
    ↓
interfaces
    ↓
world + matter
    ↓
ecology
    ↓
human
    ↓
observer (read only)
```

No lower layer may import a higher semantic layer merely to force behavior.

## File creation rule

Create files only when their phase becomes active. The tree is predetermined to prevent architectural drift, not to encourage empty scaffolding.

## Scope rule

A phase may add helpers beneath its own package, but moving ownership across top-level domains requires an ADR in `docs/architecture/ADR/`.

## First implementation target

Only these Genesis paths should be created during G0:

```text
src/hrm_genesis/__init__.py
src/hrm_genesis/config.py
src/hrm_genesis/runner.py
src/hrm_genesis/checkpoint.py
src/hrm_genesis/interfaces/authorities.py
src/hrm_genesis/interfaces/events.py
src/hrm_genesis/interfaces/snapshots.py
tests/genesis/test_g0_integration.py
qualification/genesis/run_g0_gate.py
docs/architecture/GENESIS_CAUSAL_CONTRACT.md
docs/architecture/WORLD_STATE_OWNERSHIP.md
```

Do not create plant, animal, human, or observer implementation files until their phase opens.
