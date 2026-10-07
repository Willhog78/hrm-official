# HRM Genesis Roadmap

## Purpose

Redirect HRM execution toward the smallest causally complete, autonomous world without discarding the validated Stage-1 coordination foundation.

This roadmap changes build order, not the scientific objective in `docs/HRM_MASTER_DEVELOPMENT_PLAN_v1.1.md`.

## Governing principle

**Build a world that can continue without scripted rescue before building civilization on top of it.**

The immediate target is not a full human civilization simulator. It is a small persistent ecology in which matter, energy, water, organisms, reproduction, death, depletion, regeneration, and environmental change form closed causal loops.

## Non-negotiable rules

1. Stage-1 coordination remains the active infrastructure baseline.
2. No existing Stage-1 behavior may be silently rewritten to make Genesis easier.
3. Genesis may use simplified mechanisms, but every simplification must be explicit.
4. No resource may appear merely because an organism needs it.
5. No population may be forced toward a target size.
6. No civilization, profession, institution, technology tree, faction, economy, government, or historical milestone may be scripted.
7. Observer code is read-only.
8. Every state-changing mechanism must have an owner and a causal path.
9. The world must be able to fail locally.
10. Human agents are not introduced until the non-human world can run autonomously.

---

# Phase G0 — Integration Contract

## Goal
Connect the existing Stage-1 coordination layer to a fixed Genesis kernel boundary.

## Deliverables
- world clock adapter;
- authority registration contract;
- deterministic seed namespaces;
- Genesis checkpoint bundle;
- simulation configuration schema;
- event/provenance hooks;
- minimal CLI runner.

## Exit condition
A blank world can advance, checkpoint, restore, and replay identically without any ecology enabled.

---

# Phase G1 — Physical Substrate

## Goal
Create the smallest world in which location and environmental state matter.

## Required mechanisms
- bounded 2D world grid;
- elevation;
- temperature;
- solar input;
- precipitation;
- standing/surface water;
- soil moisture;
- simple nutrient pool;
- seasonal forcing;
- local diffusion/runoff rules.

## Explicitly deferred
- full fluid dynamics;
- atmospheric circulation;
- plate tectonics;
- atom-level chemistry;
- detailed geology.

## Exit condition
The world runs for at least 10 simulated years with no organisms and exhibits deterministic seasonal and hydrological variation without state divergence or conservation failures outside declared open-system inputs/outputs.

---

# Phase G1.5 — Matter & Elements

## Goal
Replace generic environmental resource numbers with conserved elemental/material reservoirs before biology begins.

## Required mechanisms
- canonical real-element registry;
- water represented as a material reservoir with explicit H/O composition;
- per-cell elemental soil pools;
- separate Matter authority;
- hydrological transfer through Matter state;
- elemental diffusion/conservation;
- explicit open-system accounting for precipitation and evaporation;
- deterministic checkpoint/replay through Stage-1 coordination.

## Scientific status
Element identities and atomic masses are canonical reference data. Thermodynamic/reaction behavior remains deliberately limited; the quarantined Stage-2 placeholder phase constants are **not** promoted as validated science.

## Exit condition
Matter and World remain separate authorities; water and soil elements survive a 10-year run with deterministic replay and conservation within tolerance, except for explicitly accounted open-system water exchange. Plants remain blocked until this gate passes.

---

# Phase G2 — Producer Ecology

## Goal
Make primary production exist independently of consumers.

## Required mechanisms
- plant biomass;
- germination;
- growth;
- water demand;
- nutrient demand;
- light/temperature response;
- reproduction/seed dispersal;
- senescence/death;
- decomposition;
- nutrient return.

## Exit condition
Plant populations persist, migrate, boom, decline, or locally disappear from environmental conditions alone. Removing solar input or water must produce predictable collapse rather than hidden replenishment.

---

# Phase G3 — Consumer Ecology

## Goal
Add simple mobile organisms whose survival depends on the world.

## Required mechanisms
- body energy;
- hydration;
- movement cost;
- perception radius;
- foraging;
- feeding;
- rest;
- reproduction;
- aging;
- mortality;
- simple inherited traits;
- bounded learning or preference adaptation.

## Exit condition
At least two consumer populations can persist for long runs under some seeds and collapse under others. Population size must emerge from resource availability.

---

# Phase G4 — Closed Ecological Loop

## Goal
Demonstrate autonomous continuity.

## Required coupling
solar input -> plant production -> consumption -> waste/death -> decomposition -> nutrients -> plant production

Water and temperature must constrain the same loop.

## Qualification tests
- depletion;
- drought;
- overpopulation;
- local extinction;
- recovery;
- migration;
- seasonality;
- seed sensitivity;
- checkpoint/replay equivalence.

## Exit condition
A non-human Genesis world runs for 100+ simulated years without intervention and without any mechanism that injects food, organisms, or recovery because a target condition was missed.

This is the first major HRM milestone: **Autonomous Computational Ecology v1**.

---

# Phase G5 — Human Biology

## Goal
Introduce human bodies, not civilization.

## Required mechanisms
- metabolism;
- hunger;
- thirst;
- fatigue;
- thermoregulation;
- injury;
- healing;
- aging;
- reproduction;
- mortality;
- locomotion and carrying constraints.

## Exit condition
Humans can survive or die solely through interactions with the same world used by non-human organisms.

---

# Phase G6 — Human Cognition and Memory

## Goal
Give humans bounded internal state without granting global knowledge.

## Required mechanisms
- perception;
- episodic memory;
- location memory;
- individual recognition;
- expectation;
- reward/error learning;
- planning horizon;
- uncertainty;
- forgetting.

## Exit condition
Two agents exposed to different histories make different later choices despite identical immediate surroundings.

---

# Phase G7 — General Action and Communication

## Goal
Allow complex behavior to be composed from primitive actions.

## Required actions
- move;
- inspect;
- grasp;
- release;
- carry;
- consume;
- transfer;
- combine;
- separate;
- apply force;
- construct arrangement;
- signal;
- communicate;
- teach/imitate.

## Exit condition
Agents learn and transmit at least one useful behavior that is not represented in code as a named technology or milestone.

This is the second major HRM milestone: **Emergent Technique v1**.

---

# Phase G8 — Multi-Population World

## Goal
Run geographically separated populations with no scripted civilization outcome.

## Required conditions
- at least four distinct regions;
- heterogeneous ecological constraints;
- constrained travel;
- independent local histories;
- contact possible but not guaranteed.

## Exit condition
Different populations develop measurably different learned behavior or resource strategies from different causal histories.

---

# Phase G9 — Observer

## Goal
Describe what emerged without controlling it.

## Observer may classify
- settlements;
- persistent groups;
- specialization;
- exchange;
- conflict;
- hierarchy;
- cultural transmission;
- technology-like practices;
- environmental impact.

## Exit condition
Removing the Observer changes no causal simulation result.

---

# Phase G10 — Long-Run Expansion

Only after the Genesis vertical slice qualifies do we increase:
- world size;
- species variety;
- material resolution;
- disease;
- richer cognition;
- language;
- tool complexity;
- larger human populations;
- generational depth.

Depth is added where experiments show the existing abstraction is insufficient.

---

# Stop conditions

Do not advance a phase if:
- a later layer requires hidden state access;
- a causal shortcut exists only to force a desired outcome;
- conservation or accounting errors accumulate silently;
- replay cannot reproduce a surprising event;
- a subsystem survives only because the runner repairs it;
- an emergent label writes back into causal state.

# Immediate next work

G0 through G10.2 now have implementation and qualification assets in the repository.

Before the first serious long-run calibrated-human experiment, complete **G10.2A — Survival Affordance Substrate**:

1. terrain-conditioned exposed rock and cave/overhang cover;
2. woody biomass that develops only under viable plant conditions and is not automatically edible;
3. local perception of those physical affordances;
4. measurable exposure moderation from occupying real cover;
5. regression checks preserving conservation, determinism, replay, and the prior qualification stack.

After that substrate is qualified, the next experiment is long-run calibrated human survival without scripted rescue.
