# HRM — Master Development Plan v1.1

## 1. Project Objective

Build a scientifically defensible, open-ended human civilization simulation.

The simulation begins with a functioning natural world and human populations with plausible biological, cognitive, and social capacities. Human societies then develop through interaction with their environment, each other, and accumulated knowledge.

The simulation must not prescribe historical outcomes.

The purpose is to observe what develops, under what conditions, and through what causal chain.

---

## 2. Core Rule

**Predetermine the world’s rules and the humans’ capacities. Do not predetermine civilization.**

The simulation may define:

- physical laws;
- environmental processes;
- chemistry and material properties;
- biological processes;
- ecological processes;
- human physiology;
- human cognition;
- perception;
- learning;
- communication;
- reproduction;
- general physical actions;
- initial geography and population placement.

The simulation must not directly define:

- occupations;
- social classes;
- political systems;
- economic systems;
- cultural identities;
- institutions;
- technologies;
- historical eras;
- social hierarchies;
- civilization types;
- historical destinations.

Those must arise, change, persist, disappear, or never appear through the simulation itself.

---

## 3. System Architecture

HRM will use separate causal systems with explicit interfaces.

Each system owns its own state and may interact with other systems only through declared inputs, outputs, and transactions.

### 3.1 Coordination Architecture

HRM requires a shared coordination contract, but it must not become one monolithic bottleneck or one authority that owns everyone else's state.

It is divided logically into three responsibilities:

#### 3.1.1 Temporal Orchestrator

Responsible for:

- simulation time;
- scheduling;
- multi-rate synchronization;
- event ordering;
- feedback-lag policy.

#### 3.1.2 Transaction and Arbitration Fabric

Responsible for:

- read/propose/validate/commit semantics;
- simultaneous or conflicting proposals;
- deterministic conflict resolution;
- atomicity boundaries;
- stale-read handling;
- routing requests to the kernel that actually owns the affected state.

Arbitration must be partitionable or otherwise scalable. A single global queue or lock is not assumed.

#### 3.1.3 Provenance and Replay Ledger

Responsible for:

- deterministic replay evidence;
- event history;
- causal provenance;
- run/configuration fingerprints;
- audit records.

These are logical responsibilities, not a requirement for three separate processes or services. Stage 1 must determine the simplest implementation that preserves the separation while surviving realistic contention and load tests.

Each causal kernel remains authoritative for its own state. The coordination architecture governs interaction between authorities rather than becoming a universal state owner.

### 3.2 Matter and Materials

Responsible for:

- elemental composition;
- compounds and mixtures;
- physical material properties;
- temperature;
- phase/state;
- mass and energy accounting;
- physical transformation;
- fracture;
- mixing;
- separation;
- decay;
- combustion and other modeled reactions;
- material provenance.

This layer should be detailed enough to support meaningful physical and technological transformation without attempting atom-by-atom simulation.

### 3.3 Physical Environment

Responsible for:

- terrain;
- elevation;
- geography;
- water systems;
- weather;
- climate;
- seasons;
- solar input;
- soils;
- natural resource distribution;
- natural environmental change.

### 3.4 Plant Ecology

Responsible for:

- plant growth;
- reproduction;
- competition;
- water and nutrient use;
- environmental response;
- death;
- regeneration;
- ecological succession where appropriate.

### 3.5 Animal Ecology

Responsible for:

- animal populations or individuals at the appropriate level of detail;
- metabolism;
- movement;
- reproduction;
- feeding;
- competition;
- predation;
- avoidance;
- territorial behavior where appropriate;
- species-appropriate learning;
- ecological relationships.

### 3.6 Human Biology

Responsible for:

- metabolism;
- hunger and thirst;
- fatigue and sleep;
- thermoregulation;
- injury;
- healing;
- disease susceptibility;
- physical development;
- reproduction;
- aging;
- mortality;
- heritable biological variation where justified.

### 3.7 Human Cognition

Responsible for:

- perception;
- attention;
- memory;
- learning;
- prediction;
- causal reasoning;
- planning;
- problem solving;
- emotion;
- motivation;
- social cognition;
- individual recognition;
- relationship memory;
- communication;
- source-tagged second-hand and third-hand social information;
- source credibility and uncertainty;
- reputation inference from direct and communicated evidence;
- learned expectations about others' behavior;
- imitation;
- teaching;
- language;
- bounded decision-making;
- individual variation.

Agents may know only what they have perceived, learned, inferred, remembered, or received from others.

They do not have access to global simulation truth.

Social information is distributed across agents and any durable records they eventually create. HRM does not maintain an authoritative causal object called a group reputation, norm, institution, or collective belief. Shared expectations and norm-like behavior must arise when many individuals independently learn, communicate, retain, and act on overlapping social information. The Observer may classify such convergence afterward.

### 3.8 Human Action Interface

Provides general-purpose actions that connect cognition and the physical world.

Actions should operate at a low enough level that more complex behavior can be constructed from them.

Examples of action classes include:

- movement;
- observation;
- grasping and releasing;
- carrying;
- applying force;
- combining and separating materials or objects;
- constructing arrangements;
- consuming;
- transferring possession or control;
- signaling;
- communication;
- caregiving;
- other biologically available interactions.

Complex practices and technologies must emerge from combinations of actions, learning, memory, and social transmission.

### 3.9 Observer and Analysis Layer

Read-only.

Responsible for detecting, measuring, and describing higher-level patterns.

It may identify patterns in:

- population structure;
- spatial clustering;
- persistent social groups;
- kinship;
- language;
- cultural transmission;
- technology;
- specialization;
- settlement;
- exchange;
- inequality;
- conflict;
- governance;
- institutions;
- economic organization;
- environmental impact;
- demographic change;
- long-term stability or collapse.

Observer classifications never alter causal simulation state.

---

## 4. Starting World

The initial world should contain meaningful geographic and ecological variation.

Different regions may vary in:

- climate;
- rainfall;
- water availability;
- terrain;
- soils;
- plants;
- animals;
- disease ecology;
- material resources;
- mineral distribution;
- accessibility;
- seasonality;
- natural hazards.

The world should be capable of changing independently of humans.

---

## 5. Starting Human Populations

The flagship simulation begins with multiple human populations in different locations.

Starting populations should differ primarily because of:

- geography;
- local ecology;
- available materials;
- travel constraints;
- contact opportunities;
- inherited biological variation within defensible bounds;
- whatever cultural knowledge is explicitly appropriate to the selected historical starting condition.

No population receives built-in advantages or disadvantages tied to a named social identity.

Persistent groups should be detected from interaction patterns rather than permanently assigned as fixed factions.

---

## 6. Learning and Knowledge

Knowledge exists in individuals and in whatever durable representations the agents eventually create.

A useful behavior or technique should have a traceable causal history:

1. experience or observation;
2. memory;
3. attempted reuse;
4. success or failure;
5. learning;
6. imitation or teaching;
7. transmission;
8. modification;
9. retention or loss.

Knowledge can spread.

Knowledge can diverge.

Knowledge can be forgotten.

Different populations can arrive at different solutions to similar problems.

---

## 7. Emergence Standard

A higher-level phenomenon counts as emergent only if:

- it was not directly encoded as a target state;
- it was not granted by a hidden shortcut;
- it arises from lower-level causal mechanisms;
- it can fail to appear;
- it can appear differently under different conditions;
- its history can be reconstructed from simulation evidence.

---

## 8. Scientific Qualification

Every meaningful mechanism receives one of four statuses:

### Validated
Causally active and supported against relevant independent evidence.

### Live but unvalidated
Causally active, but empirical calibration or validation remains incomplete.

### Structural
Present in architecture or state but not currently affecting outcomes.

### Rejected
Unsupported, misleading, redundant, hard-coded, or incompatible with the project rules.

Important mechanisms must be tested for:

- execution;
- causal effect;
- determinism where expected;
- sensitivity;
- ablation;
- stability across seeds;
- coupling effects;
- comparison with appropriate external evidence.

### 8.1 Qualification and Freeze Cycle

HRM deliberately keeps the useful rigor of the prior project without reproducing unnecessary ceremony.

Every causal stage follows:

**BUILD → QUALIFY → ADVERSARIAL REVIEW → DECIDE → FREEZE → ADVANCE**

Before a stage freezes:

- exit criteria are written before confirmatory testing;
- at least one hostile/falsification case targets each important invariant or boundary;
- negative results are retained;
- coupling tests are rerun whenever a new dependency changes feedback topology;
- defects found in review are corrected and the affected evidence is rerun;
- a frozen stage is reopened only when evidence shows that its contract or implementation is insufficient.

Independent architecture review is mandatory before freezing the foundational/high-coupling stages: Coordination Architecture, Matter/Materials, Human Cognition, Social Learning/Reputation, Multi-Population Baseline, and Observer Layer.

Other stages still require adversarial qualification, but may use a lighter review unless risk or failures justify escalation.

---

## 9. Build Order

### Stage 0 — Canon and Salvage Audit

Review prior HRM and Age of Agentus work through an explicit, auditable salvage table.

For every candidate mechanism, record:

| Field | Required content |
|---|---|
| Source | File/module/build lineage |
| Mechanism | What the prior implementation actually does |
| Prior evidence | Tests, failures, measurements, and known limitations |
| HRM disposition | KEEP / ADAPT / REWRITE / REJECT / DEFER |
| §8 status | Validated / Live but unvalidated / Structural / Rejected |
| Reason | One-sentence causal/scientific justification |
| Dependency | Which HRM stage, if any, may use it |

**Important:** passing prior internal tests does not by itself make a mechanism `Validated` under §8. External/independent empirical support is still required where the mechanism makes an empirical claim.

The minimum inventory must include:

- Reality Contract and cross-kernel interface rules;
- transaction/arbitration and deterministic replay machinery;
- identity and provenance handling;
- Matter conservation and transformation machinery;
- synchronization and feedback-lag tests;
- prior cognition/learning mechanisms, including prediction-based learning;
- HRM environmental mechanisms such as seasonality, depletion/regeneration, travel costs, and heterogeneous resource opportunity;
- prior social, faction, role, innovation, settlement, governance, or economic mechanisms that may contain hard-coded outcomes.

The output of Stage 0 is the salvage table itself, not a prose recollection of what seemed useful.

### Stage 1 — Coordination Architecture
Build and qualify the Temporal Orchestrator, Transaction/Arbitration Fabric, and Provenance/Replay Ledger.

Load-test arbitration and shared authorities under realistic contention before later kernels depend on them. The implementation must demonstrate that scheduling and replay do not require all causal work to serialize through a single global bottleneck.

### Stage 2 — Matter and Materials
Build material composition, physical properties, transformation, and conservation.

### Stage 3 — Physical World
Build terrain, water, weather, climate, seasons, soils, and geographic variation.

### Stage 4 — Plant Ecology
Build functioning producer ecology.

### Stage 5 — Animal Ecology
Build functioning animal ecology.

### Stage 6 — Human Biology
Build humans that can physically live, reproduce, develop, become injured, recover, age, and die.

### Stage 7 — Human Cognition
Build perception, memory, learning, planning, reasoning, emotion, and social cognition.

### Stage 8 — General Human Action
Connect cognition to physical action in the world.

### Stage 9 — Social Learning, Reputation, and Communication
Support imitation, teaching, communication, relationship memory, intergenerational knowledge transfer, and source-sensitive second-hand/third-hand social learning.

Required qualification includes:

- information about an absent person can propagate through communication;
- recipients track who supplied the information and with what confidence;
- direct evidence can reinforce or contradict communicated claims;
- socially transmitted information can change later expectations and choices without granting global truth;
- shared expectations can arise across multiple agents without a pre-authored norm object;
- removing or corrupting the transmission mechanism measurably changes those effects.

This stage does **not** add a group-level causal authority for norms, reputation, governance, or institutions.

### Stage 10 — Multi-Population Baseline
Place multiple populations into different environments with no scripted civilizational outcomes.

**Provisional qualification workload:** begin with at least 200–500 simultaneously active humans distributed across at least four geographically distinct populations and run for at least 10 generations, or until genuine model-caused extinction. These are engineering/experimental floor targets, not claims that any social phenomenon must appear at that scale.

### Stage 11 — Observer Layer
Add read-only detection of social, technological, demographic, economic, political, cultural, and ecological patterns.

### Stage 12 — Long-Run Experiments
Run many seeds and compare outcomes across generations.

**Provisional long-run target:** demonstrate a qualified workload capable of at least 2,000 simultaneously active humans, at least eight regional populations, and at least 50 generations, with smaller and larger sensitivity runs around that workload. A run may end earlier through model-caused extinction or collapse and still be scientifically informative.

These numbers are revisable engineering targets. Stage 7–10 profiling may change them before Stage 12 is frozen. They must never be used as post-hoc thresholds for declaring that institutions, hierarchy, technology, or any other outcome “should have” appeared.

### Stage 13 — Expansion
Add deeper scientific resolution only where the existing model demonstrates a need for it.

---

## 10. First Executable Target

Do not begin with the entire civilization simulator.

Build one small vertical slice that contains:

- heterogeneous terrain;
- water;
- weather;
- material properties;
- plants;
- animals;
- human biology;
- human cognition;
- general physical interaction;
- communication;
- more than one local population;
- read-only observation.

The first major proof is:

> Human agents learn and transmit at least one useful behavior or material technique that was not represented in the code as a named technology or scripted milestone.

---

## 11. Development Discipline

- One active stage at a time.
- Each stage has explicit entry and exit criteria written before confirmatory testing.
- Each causal stage follows the qualification/freeze cycle in §8.1.
- Each subsystem must qualify independently before coupled qualification.
- New mechanisms require a clear causal purpose.
- Higher-level labels never control lower-level behavior.
- Observer output never writes back into the simulation.
- No mechanism is accepted merely because it sounds plausible.
- No feature is counted as realism unless it actually affects the model.
- No technology tree.
- No historical script.
- No predetermined social order.
- No predetermined endpoint.
- No casual conversation, example, question, joke, or speculation changes this plan.
- Scientifically necessary implementation details may be added when required to make an already-approved subsystem work, but they must remain subordinate to that subsystem rather than becoming new project themes.

---

## 12. v1.1 Revision Decisions

This revision evaluated five external review proposals individually.

1. **Persistent group-level social layer — PARTIALLY ACCEPTED.**  
   The missing capability is real: humans need source-sensitive second-hand/third-hand social information and reputation inference. A persistent causal group/norm/institution authority is rejected because it would pre-install the higher-level phenomena §2 and §7 require to emerge. The accepted mechanism is distributed across individual cognition, communication, memory, and later durable records.

2. **Population scale and time horizons — ACCEPTED AS PROVISIONAL ENGINEERING TARGETS.**  
   Stages 10 and 12 now contain explicit workload/generational targets. They are revisable after profiling and cannot become outcome thresholds.

3. **Concrete Stage 0 salvage list — ACCEPTED.**  
   Stage 0 now produces an auditable table with disposition, evidence, §8 status, and rationale. Prior internal qualification is kept distinct from empirical validation.

4. **Reality Coordinator over-centralization — ACCEPTED AS A RESTRUCTURE.**  
   Coordination is split logically into temporal orchestration, transaction/arbitration, and provenance/replay. This does not require microservices; it prevents the architecture from assuming one global authority or lock.

5. **Adversarial stage closure — ACCEPTED IN TIERED FORM.**  
   Every causal stage gets hostile/falsification testing. Independent architecture review is mandatory for foundational/high-coupling stages and optional/escalated elsewhere.

---

## 13. Decision Test

Before adding anything to HRM, ask:

> Does this represent a real causal capability, constraint, process, or measurement that the accepted simulation requires?

If yes, define and test it.

If it directly supplies a historical outcome instead, it does not belong in the causal model.
