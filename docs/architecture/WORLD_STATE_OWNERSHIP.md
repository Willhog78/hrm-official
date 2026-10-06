# World State Ownership

## Rule

**There is no universal Genesis state owner.**

Each causal domain owns only the state it is responsible for. Coordination routes legal interactions between owners.

## Ownership map

| Domain | Owns | Must not own |
|---|---|---|
| Coordination | time, arbitration, replay/provenance, coordination checkpoints | terrain, resources, organisms, cognition |
| World (G1) | spatial/environmental state | organisms, human memory, observer labels |
| Matter (G1+) | declared material pools/transfers | ecological goals, technologies |
| Ecology (G2+) | plant/animal organism or population state | climate truth, human cognition |
| Human (G5+) | body and cognition state | global simulation truth |
| Observer (G9) | derived measurements/classifications only | any causal state |

## G0 system authority

The `genesis.system` authority contains only the logical tick marker needed to qualify runner/checkpoint/replay wiring.

It is not permission to create a global dictionary of later world state.

## G1 physical-world authority

The G1 authority is:

- authority: `world.environment`
- resource: `state`

Its state contains only physical-environment information: bounded coordinates, elevation, temperature, solar input, precipitation, surface water, soil moisture, nutrients, and cumulative open-system water accounting.

It does not contain plants, animals, humans, social state, observer labels, target populations, or repair instructions.

For G1 the physical state is carried through the existing Stage-1 authority adapter so transaction, replay and checkpoint semantics remain exercised. Semantic ownership is nevertheless separate from `genesis.system`; future ecology/human phases must create their own authorities rather than append state to `world.environment`.

## Cross-domain rule

If an operation changes state owned by more than one authority, it must be represented as a Stage-1 transaction spanning those authorities.

## Dependency rule

Lower-level causal domains must never import higher-level semantic labels to decide outcomes. In particular:

- world physics does not know settlements;
- plant ecology does not know economies;
- animal ecology does not know institutions;
- human biology does not know professions;
- cognition does not receive observer classifications as truth;
- observer classifications never feed back into the simulation.
