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

**Ecology opportunity investigation** (owner decision, 2026-10-07). Cognition work is paused until it is done. Opening: `docs/architecture/ECOLOGY_OPPORTUNITY_OPENING.md`.

1. **Measure.** For every independent agent-day, measure how often an agent:
   - is hungry;
   - lacks reachable known food;
   - has another agent nearby;
   - witnesses a useful act.

   Report each condition separately, and their overlap, by year and season. Tool: `python -m qualification.genesis.opportunity`, read-only, with a ledger-digest check.
2. **Propose controlled experiments** comparing the existing world with:
   - physically justified food patchiness;
   - seasonal variation;
   - population density.

   Preserve the baseline and the conservation checks. Count opportunities separately from successful following or imitation.
3. **Decide the pending owner calls** recorded in the opening, with concrete consequences:
   - predation on Agentus;
   - animal life history;
   - default physiology.

**Rule.** Animal reproduction is not raised, and agents are not crowded together, merely to make cognition produce a result. Each world change needs a biological or environmental justification stated before its result is known.

**Milestone.** An explanation of the missing opportunities, even if it is that following and imitation have little value in this world.

**Progress (2026-10-07).**
- Step 1 (measurement) is done. Following has no opportunity because food is abundant and in view. Useful acts are rare at the source, so imitation has little to draw on. Co-presence is low only in the founding months.
- D2 units fix: done (`docs/architecture/D2_CONSUMER_TIMEBASE.md`).

Next, in order (owner decision, 2026-10-08):
1. ~~Reconcile the reserve counts.~~ Done: the consumer timebase explains 400 versus 34.
2. Elapsed-time movement and encounter opportunities. `elapsed-time-v2` is done. The residual population-level difference is traced to plant rates that are not timebase-converted, and to destination scoring by standing biomass; both are proposed, not implemented.
3. Separate nursing (milk), weaning and longer childhood dependence before changing birth spacing or milk cost. `reference-v1` stays the default.
4. Complete the predation decision (D1) and its physical pathway: attempt, resistance or escape, injury, possible death, accessible tissue, possible consumption. Defensive bites stay separate.
5. Reassess useful acts and social learning in the corrected world.

Cognition stays paused. E1–E3 stay on hold. Preparation acts earn credit only when a real later benefit traces back to them.

E1–E3 remain proposals and are not the next step. Higher density is not supported by the census.

## G10.2A — Survival affordance substrate (complete)

Merged in PR #19:
- terrain-conditioned exposed rock and cave/overhang cover;
- woody biomass grown only under viable plant conditions and not automatically edible;
- local perception of these affordances;
- exposure moderation from occupying real cover;
- regression checks.

Gate: `qualification/genesis/run_g10_2a_survival_affordance_gate.py`.

## G10.3 — Agentus natural capacities (capacity model v1)

Implemented behind `agentus_capacities_enabled`. The specification and audit are in `docs/architecture/G10_3_AGENTUS_CAPACITIES.md`.

The new abilities:
- omnivorous ingestion;
- fresh vs decayed carcass tissue;
- capture of live animals;
- movable stone with fracture and edges;
- plant, bark and tendon fibers;
- bindings that hold or fail;
- worn surfaces;
- learned food and interaction values;
- travel toward remembered food.

First evidence: `experiments/genesis/summaries/AGENTUS_CAPACITY_V1_2026-10-07.md`. The capacities work and conserve material. Over two years on four seeds, they did not change survival reliably. Dehydration dominates every arm.

### Outcome (superseded plan)

The plan that stood here has been carried out or replaced:
- thirst was decided and implemented (G10.4);
- animal abundance was diagnosed (life history is the limit; owner decision pending);
- learning was extended (G10.4);
- the 20-seed batches were run.

Long batches are no longer the advancement gate (see G10.6 and `docs/architecture/TESTING_TIERS.md`).

## G10.4 — Survival bottlenecks (complete)

Thirst became a baseline drive. Hunting requires physical approach and contact. Delayed credit flows through object history. Repeated use is measured, and successes are transmitted by observation. Details: `docs/architecture/G10_4_SURVIVAL_BOTTLENECKS.md`.

## G10.5 — Energy-budget realism (complete, opt-in)

`reference-v2` physiology adds a fat reserve, lean catabolism, corrected nursing and Kleiber scaling. It is opt-in, and the default stays `reference-v1`.

## Testing tiers and advancement rule

There are four tiers: micro, smoke, diagnostic and full. Work iterates on `fast` (micro + smoke, about 30 s). A targeted diagnostic confirms outcome-level effects. The full 730-day batch supports long-run claims only.

A mechanism advances when its physical and integrity contract holds:
- thirst is physical;
- hunting needs contact;
- omnivory is capability, not knowledge;
- stone and fibres obey material constraints;
- ledgers, balance and determinism hold.

This applies even while the ecology still has unsolved mortality.

## G10.6 — Behavioural and locomotion integrity (implemented)

Three causal-model defects exposed by the micro tier are corrected as a versioned baseline (`agentus_behavior_integrity_enabled`, default on; off reproduces pre-G10.6):
1. **Partial-food abandonment.** A hungry agent no longer walks away from reachable food just because it cannot cover a full day. A declared giving-up level of 25% of daily need applies.
2. **Dependent teleportation.** A co-located dependent is carried; a separated one walks one cell a day. Dependents act after caregivers.
3. **Fatigue saturation.** Sleep recovers a fraction of fatigue every night, so daily walking settles at about 0.24 instead of 1.0, and interaction is no longer suppressed for large parts of life.

Each passed micro, then smoke, then the targeted diagnostic (`diagnostic integrity`). Details: `docs/architecture/G10_6_BEHAVIORAL_INTEGRITY.md`.

## G10.7 — Communication and teaching (G10.7a steps 1–4 implemented; paused)

G7 promises signal, communicate and teach/imitate. G10.4 supplies observation of successes and delayed credit. The next layer bridges isolated useful acts and persistent transmitted practice, without hard-coding technology:
- signals produced by bodies and perceived locally, with no shared vocabulary preloaded;
- demonstration and imitation of interaction sequences, not only single outcomes;
- teacher-learner asymmetry (caregivers and dependents) under the same physical-access rules;
- measures of practices that persist across individuals and generations.

Implemented so far (G10.7a, PRs #29–#33):
- leak closure;
- witnessed-event memory;
- retention by visible consequence;
- imitation as a bias on what to try;
- following learned from the agent's own experience.

Step 5 (measurement) and G10.7b (the costly call) wait on the ecology opportunity investigation above. In its diagnostic, following never had an opportunity, and the reason must be explained before more is built.

Later G10 candidates: richer cognition, tool complexity, disease, larger populations, generational depth.

## Infrastructure

GitHub Actions has never run. Every job since run 1 has been refused with "account is locked due to a billing issue". Restoring it needs the account owner to resolve billing, then a workflow update (see `STATUS.md`, "Verification infrastructure"). Until then, the local tiers and gate scripts are the verification record.

## Experienced transition learning — owner resumption (2026-10-09)

The owner authorized beginning the bounded transition extension. This resumes
this specific cognition work despite the older pause above. Stage 1 is opt-in,
write-only recording of own local before/action/after experience and real costs;
physical action choice and production defaults remain unchanged. Sequence
valuation and sequential imitation require separate evidence before activation.
Contract and verification: `docs/architecture/EXPERIENCED_TRANSITIONS_V1.md`.

### Conditional sequence valuation — opt-in v2 (2026-10-09)

Owner-authorized continuation adds bounded conditional expected value and
reserve-funded live choice over experienced short chains. Food credit is bounded
by actual received energy; newly changed cover/worn material receives only its
marginal first-tick thermal benefit. Default and v1 recording remain available.
Evidence and limits: `docs/architecture/SEQUENCE_VALUATION_V2.md`. Longer delayed
thermal returns and sequential imitation remain separate validation steps.

### Delayed thermal returns — opt-in v3 (2026-10-09)

Owner-authorized continuation tracks up to two own material contributions over
32 ticks. Discounted actual thermal savings can repay an originating attempt;
transfer, departure, physical intervention, forgetting and expiry end credit.
Default, v1 and v2 remain available. Controlled valuation works; autonomous
ecological discovery and sequential imitation remain unproven. Contract and
verification: `docs/architecture/DELAYED_THERMAL_V3.md`.

### Own procedural continuity — opt-in v4 (2026-10-09)

Owner-authorized continuation joins repeatedly observed own consecutive material
transitions over a six-action horizon, including repeated progress and overnight
bodily drift. Every step still uses current physical options and reserve guards;
the three-interaction tick limit remains. Controlled four-action stone preparation
replays across ticks; independent ecological discovery and sequential imitation
remain unproven. Contract: `docs/architecture/PROCEDURAL_CONTINUITY_V4.md`.

### Untrained discovery census — read-only (2026-10-09)

Three seeds × 365 days, baseline and wind/subcell V4, with six unobserved twins
and three additional thermal-exposure probes, all preserve ledger parity.
Agents spontaneously interlace/wear and arrange material, but measured protection
is negligible and useful stone/food overlap is rare. Physical placement/work scale
is the next boundary; no cognition, physics or production behavior was changed.
Report: `experiments/genesis/summaries/DISCOVERY_DIAGNOSIS_V4_2026-10-09.md`.
