# World State Ownership

## Rule

**There is no universal Genesis state owner.**

Each causal domain owns only the state it is responsible for. Coordination routes legal interactions between owners.

## Ownership map

| Domain | Owns | Must not own |
|---|---|---|
| Coordination | time, arbitration, replay/provenance, coordination checkpoints | terrain, resources, organisms, cognition |
| World (G1) | coordinates, elevation, temperature, solar input, precipitation | material inventories, organisms, observer labels |
| Matter (G1.5+) | water reservoirs, elemental pools, conserved material transfers | climate generation, ecological goals, technologies |
| Ecology (G2+) | producer biomass/seeds/detritus and, in G3, individual consumers/carcasses | climate truth, environmental Matter reservoirs, human cognition |
| Human (G5+) | body and cognition state | global simulation truth |
| Observer (G9) | derived measurements/classifications only | any causal state |

## Authorities

`genesis.system` owns only the logical tick marker.

`world.environment` owns the physical forcing field: terrain, temperature, solar input and precipitation.

`matter.environment` owns environmental material inventory. In G1.5 that means surface water, soil water and per-cell elemental pools.

There is deliberately no second copy of water or nutrients in World state. G2 also forbids Ecology from copying those reservoirs: producer growth must debit the Matter authority through an atomic cross-authority transaction.

## Matter bridge

The G1.5 Matter layer uses a canonical element registry and tracks biologically/materially relevant elements separately. Water remains a compound reservoir, with its H/O elemental consequence available through accounting rather than duplicated as an independent store.

The quarantined Stage-2 Slice-A work informed the conservation and ownership rules. Its illustrative thermodynamic threshold table is not promoted into Genesis as validated physics.

## Cross-domain rule

If an operation changes state owned by more than one authority, it must be represented as a Stage-1 transaction spanning those authorities. A kernel may legally read declared projections of another authority without taking ownership of that state.

## Dependency rule

Lower-level causal domains must never import higher-level semantic labels to decide outcomes. In particular:

- world physics does not know settlements;
- matter does not know organisms or technologies;
- plant ecology does not know economies;
- animal ecology does not know institutions;
- human biology does not know professions;
- cognition does not receive observer classifications as truth;
- observer classifications never feed back into the simulation.
