# HRM Predetermined File Tree

This tree is the target structure for the Genesis vertical slice. As of 2026-10-07 it is reconciled with the files that exist; entries marked *planned* do not exist yet.

Existing Stage-1 files remain in place. New implementation should conform to this layout unless a documented architecture decision explicitly changes it.

```text
hrm-official/
├── README.md
├── STATUS.md                      # detailed status; README must agree with it
├── ROADMAP.md
├── FILE_TREE.md
├── pyproject.toml
├── .github/workflows/stage1.yml   # never run (account billing lock); see STATUS
│
├── docs/
│   ├── HRM_MASTER_DEVELOPMENT_PLAN_v1.1.md
│   ├── architecture/
│   │   ├── GENESIS_CAUSAL_CONTRACT.md
│   │   ├── WORLD_STATE_OWNERSHIP.md
│   │   ├── HOMO_AGENTUS_TERMINOLOGY.md
│   │   ├── TESTING_TIERS.md
│   │   ├── G4_AUTONOMY_QUALIFICATION.md
│   │   ├── G5_HUMAN_BIOLOGY.md
│   │   ├── G6_COGNITION_MEMORY.md
│   │   ├── G7_GENERAL_ACTION_COMMUNICATION.md
│   │   ├── G8_MULTI_POPULATION.md
│   │   ├── G9_OBSERVER.md
│   │   ├── G10_1_SCALE_SUBSTRATE.md
│   │   ├── G10_2_HUMAN_CALIBRATION.md
│   │   ├── G10_2A_SURVIVAL_AFFORDANCES.md
│   │   ├── G10_3_AGENTUS_CAPACITIES.md
│   │   ├── G10_4_SURVIVAL_BOTTLENECKS.md
│   │   ├── G10_6_BEHAVIORAL_INTEGRITY.md
│   │   ├── G10_7_COMMUNICATION_TEACHING.md
│   │   ├── ECOLOGY_OPPORTUNITY_OPENING.md   # current focus
│   │   └── ADR/                    # planned; no ADR written yet
│   └── stage0/
│       └── HRM_STAGE0_SALVAGE_LEDGER_v1.1.md
│
├── src/
│   ├── hrm_coordination/          # Stage-1 foundation
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
│       ├── world/
│       │   ├── grid.py
│       │   ├── state.py
│       │   ├── terrain.py
│       │   ├── climate.py
│       │   ├── water.py
│       │   ├── soil.py
│       │   └── energy.py
│       ├── matter/
│       │   ├── elements.py
│       │   ├── pools.py
│       │   ├── transfers.py
│       │   ├── objects.py         # G10.3 material physics (stone, fiber, binding)
│       │   └── accounting.py
│       ├── ecology/
│       │   ├── plants.py
│       │   ├── decomposition.py
│       │   ├── animals.py
│       │   ├── populations.py
│       │   ├── autonomy.py
│       │   └── traits.py
│       ├── human/
│       │   ├── biology.py
│       │   ├── calibration.py     # G10.2 reference physiology
│       │   ├── perception.py
│       │   ├── memory.py
│       │   ├── learning.py
│       │   ├── planning.py
│       │   ├── actions.py
│       │   ├── diet.py            # G10.3 ingestion by food kind
│       │   ├── interactions.py    # G10.3+ live interactions, witnessed memory, imitation, following
│       │   ├── regions.py
│       │   └── communication.py
│       ├── observer/
│       │   ├── metrics.py
│       │   ├── ecology.py
│       │   ├── population.py
│       │   └── emergence.py
│       └── interfaces/
│           ├── authorities.py
│           ├── events.py
│           └── snapshots.py
│
├── tests/
│   ├── test_stage1_coordination.py
│   ├── test_stage1_hmt_contract.py
│   └── genesis/
│       ├── test_g0_integration.py … test_g9_observer_isolation.py
│       ├── test_g10_3_agentus_capacities.py
│       ├── test_g10_4_{encounters,learning,thirst}.py
│       ├── test_g10_5_physiology.py
│       ├── test_g10_7_memory_non_causal.py
│       ├── test_{food_intake_diagnosis,plant_lifecycle,reproduction_contact,survival_affordances,tier_observer}.py
│       └── micro/                 # micro tier: test_micro_<topic>.py + _scenario.py
│
├── qualification/
│   ├── hmt_stage1_gate.py
│   ├── reproduce_stage1.py
│   ├── benchmark_stage1.py
│   └── genesis/
│       ├── run_g0_gate.py … run_g10_2a_survival_affordance_gate.py   # phase gates
│       ├── run_agentus_development_gate.py
│       ├── run_conditional_adaptation_gate.py
│       ├── run_physical_interaction_substrate_gate.py
│       ├── run_predator_gate.py
│       ├── run_weather_persistence_gate.py
│       ├── tiers.py               # micro / smoke / diagnostic / full / fast
│       ├── smoke.py
│       ├── diagnostic.py
│       ├── tier_observer.py       # read-only observer for smoke and diagnostic
│       ├── opportunity.py         # read-only social-learning opportunity census
│       ├── report_g4_results.py
│       └── scenarios/
│
├── experiments/
│   └── genesis/
│       ├── run_*.py, run_*.sh     # multiseed, diagnosis and long-run scripts
│       └── summaries/             # dated experiment summaries and JSON
│
├── evidence/                      # dated verification records (flat; per-phase folders not created)
├── governance/
├── reviews/
├── journals/
├── drafts/                        # stage2 (quarantined)
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
