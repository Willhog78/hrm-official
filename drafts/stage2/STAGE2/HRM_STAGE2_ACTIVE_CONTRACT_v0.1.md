# HRM Stage 2 — Matter and Materials — Active Entry Contract v0.1

**Status:** ACTIVE / AUTHORIZED FOR STAGE-2 FIRST-SLICE IMPLEMENTATION
**Controlling plan:** HRM Master Development Plan v1.1, §3.2 and §10 (First Executable Target)
**Entry authorization:** Stage 1 frozen/closed 2026-09-15 (external adversarial review PASS after correction)
**Upstream inheritance (per Stage-0 salvage ledger):** Agentus Gate 2 — Matter entities + field
reservoirs (KEEP), mass/momentum/energy accounting (KEEP), abstract material component registry
(ADAPT → real elemental/compound properties), transformation/split/merge machinery (ADAPT)

## Scope discipline (§10 vertical-slice rule)

Master Plan §3.2 defines Matter/Materials as covering elemental composition, compounds/mixtures,
physical properties, temperature, phase/state, mass/energy accounting, transformation, fracture,
mixing, separation, decay, combustion, and material provenance. Building all of that before any
of it has run against real causal state would violate §10's instruction not to begin with the
entire simulator.

**This contract covers Stage-2 Slice A only:** the causal substrate — real elemental/compound
composition, mass and energy conservation as enforced invariants (not decoration), phase/state as
a function of composition and thermal energy, and the generic transformation operations (split,
merge, mix, phase change) that later fracture/decay/combustion mechanisms will be built from.

**Explicitly deferred to Slice B (not this contract, not authorized by it):** combustion and other
named reactions, decay kinetics, fracture mechanics, and any specific chemistry beyond generic
mass/energy-conserving composition mixing. Deferring these is not scope-cutting for convenience —
per the salvage ledger, chemistry expansion was already explicitly assigned to a later Stage-2 pass
at Stage-0 closure.

Stage 2 is **not** authorized to introduce climate/weather, ecology, biology, cognition, or social
semantics. Matter entities have no agency, no goals, and no named technological or economic role.

## Predeclared Slice-A exit criteria

| ID | Required result |
|---|---|
| M2.1 Composition realism | A material's identity is defined by element/compound composition (mass fractions), not an opaque registered ID. Two materials with identical composition are physically interchangeable; two with different composition are not silently treated as equal. |
| M2.2 Mass conservation | Every transformation (split, merge, mix, phase change) conserves total mass to floating-point tolerance across all participating entities/reservoirs. No transformation may create or destroy mass. |
| M2.3 Energy accounting | Every entity/reservoir carries an explicit internal energy quantity. Phase change consumes/releases energy consistent with a declared latent-heat model; mixing and merging conserve total energy to tolerance. No transformation may create or destroy energy. |
| M2.4 Phase determination is derived, not authored | Phase/state (solid/liquid/gas) is computed from composition-weighted phase-transition thresholds and current thermal energy, never set directly by calling code. Crossing a threshold changes phase; changing phase without crossing a threshold is illegal. |
| M2.5 Split conservation | Splitting one entity into N parts conserves mass, energy, and composition ratios across all parts to tolerance. The original entity's identity does not survive as a privileged "parent" with special properties. |
| M2.6 Merge/mix conservation | Merging or mixing two or more entities produces one entity whose composition is the mass-weighted union of inputs, with mass and energy conserved to tolerance. Order of merge inputs does not change the result (associativity/commutativity to tolerance). |
| M2.7 Ownership/authority boundary | Matter entities remain owned by the Matter authority under the Stage-1 fabric's authority/commit interface. No later-stage kernel may mutate Matter state directly; all changes route through declared transformation proposals. |
| M2.8 Determinism | Same initial composition/energy state plus same sequence of transformation operations produces bit-identical resulting state and digest, matching the Stage-1 replay contract. |
| M2.9 No hidden material catalog privilege | No material/element is hardcoded with a name-based special case in transformation logic (e.g. no `if element == "gold": ...`). All transformation math operates on numeric properties (atomic/molar mass, specific heat, latent heat, phase thresholds), not on name matching. |
| M2.10 Conservation under adversarial composition | Conservation (M2.2, M2.3) holds under adversarial inputs: zero-mass entities, single-element entities, entities at exact phase-transition boundaries, and split into a large N (stress case). |

## Required adversarial cases before freeze

- split into 1 (identity case) and split into a large N;
- merge of entities with disjoint vs. overlapping composition;
- phase change exactly at the transition boundary (numerical edge case);
- repeated split→merge round trip must return to the original composition/mass/energy within tolerance;
- attempted direct mutation of Matter state bypassing the transformation interface (must be rejected the same way Stage 1 rejects illegal private-state writes);
- mass/energy conservation check across a long random sequence of transformations (stress/fuzz case), not just hand-picked examples.

## Freeze rule

Slice A requires the same qualify → adversarial review → decide → freeze cycle as Stage 1. Slice B
(combustion/decay/fracture/named reactions) is a separate contract and is not opened by this one.
