# G10.3 — Agentus Natural Capacities (capacity model v1)

Governing principle: **providing natural capacities and physical possibilities is different from supplying a predetermined outcome.**

This phase gives Homo agentus enough biological, perceptual, and manipulative capacity to discover useful behavior, without guaranteeing survival or scripting technique. Everything here is gated behind `GenesisConfig.agentus_capacities_enabled` (default `False`). With the flag off, every earlier configuration, fingerprint, ledger, and result is unchanged.

---

## 1. Capability audit of `main` (commit `d7bfbcc`)

Classification key: **IMPL** implemented and live · **DISC** implemented but disconnected from live runs · **ABST** abstract qualification demonstration only · **VOCAB** vocabulary with no live effect · **ABSENT** not represented.

| Capacity | Status | Evidence |
|---|---|---|
| Plant tissue as food | IMPL | `human/biology.py:231-273` — `_food_mass` and `_eat` read and debit only `plant_elements_kg`; 2200 kcal/kg dry × assimilation 0.80. |
| Seeds as food | ABSENT for Agentus | `ecology/plants.py` `seed_elements_kg` is consumed only by germination (`plants.py:206-214`). Neither Agentus nor animals eat seeds. |
| Roots / tubers / fruit | ABSENT | No such pools exist in the producer substrate. |
| Animal food for Agentus | ABSENT | Predators kill prey (`ecology/animals.py:297-333`); carcasses decompose (`animals.py:537-546`). No organism scavenges and Agentus have no animal interaction. |
| Agentus ↔ animal interaction | One-way only | `biology.py:533-556` lets co-located predators injure Agentus. `consumer_state` reaches `evolve_humans` read-only (`biology.py:568`, `runner.py:515-524`). |
| Carcass freshness / spoilage | ABSENT | Carcass cells are one undifferentiated pool. |
| `consume` primitive | VOCAB | Listed in `human/actions.py:7-10`; `execute_live_sequence` (`actions.py:48-145`) has no branch for it (nor for `move`, `transfer`, `signal`). Only the abstract toy (`actions.py:162-190`) handles `consume`. |
| Live manipulation | DISC | `biology.py:626` runs `execute_live_sequence` only when `learned_sequences` is non-empty. It starts empty (`biology.py:93`, `:334`) and only `communication.imitate_signal` fills it. The runner never calls that, so **no live manipulation happens in any live run**. G7 and the physical-interaction gate exercise it only in fixtures. |
| Wood manipulation | DISC | `actions.py` moves woody element mass between woody/loose/arranged/held pools; arranged geometry moderates exposure (`biology.py:422-440`). Reachable only through the disconnected path above. |
| Stone | Terrain statistic only | `world/grid.py:59` computes `rock_exposure`; perception reports it (`human/perception.py:52`); nothing can grasp, strike, or break stone. |
| Fibers | ABSENT | No fiber material, properties, or manipulation anywhere in `src/`. |
| Binding / combining | ABST | `combine` moves loose wood into the arranged pool with no constraint semantics (`actions.py:128-133`). |
| Learning about resources or actions | ABSENT | `human/learning.py` learns location-keyed reward only. No learning about food kinds, materials, or interactions. |
| Remembered places in planning | Partial | `memory.py` stores seen locations; `planning.py` uses memory only for visit counts during hungry exploration (`planning.py:31-55`), never to travel back to remembered food. |
| Infant feeding | IMPL | Full dependence means no self-feeding; caregiver provisioning (`biology.py:374-419`, `:638-642`). |
| Ownership path for animal food | Available | The Agentus transaction already spans Matter, Ecology, Consumer, and Human authorities atomically (`runner.py:526-559`). No new authority is needed. |

### Measured substrate (seed `agentus-demography-a`, the existing multiseed configuration, day 30)

- 8 Agentus (28 kg dry, 2000 kcal/day basal each, gut cap 1.35 kg dry/day).
- Edible plant tissue 2460 kg dry; seeds 365 kg dry; woody 0 kg (woody growth needs ≥30 ticks of age and condition ≥0.60).
- **5 animals world-wide, 12–60 g dry each.** `material_scale_factor` scales soil and plants but not the consumer ecology (`animals.py:115`, `traits.py`). All animal tissue in the world holds less energy than one Agentus needs in a day.

The last point is the main limit on interpreting animal food. This phase builds a real animal-food pathway. Changing animal abundance or body size would change the environment's resources, which needs separate authorization. Section 6 records it as a pending calibration decision.

---

## 2. Structural risk assessment (written before implementation)

| Risk | Assessment | Mitigation |
|---|---|---|
| **State ownership** | Agentus kills and scavenging mutate Consumer state; stone pickup mutates Matter state; fiber and wood extraction mutate Ecology state. | All happen inside the existing four-authority Agentus transaction. Consumer-side rules (removing a killed animal, displacing an escaping one, the fresh-tissue pool) live in `ecology/animals.py`; the Agentus kernel calls them. Natural loose stone is a Matter inventory. Objects once handled are owned by the Agentus authority, like `remains_cells` and held material today. `matter/objects.py` holds material physics only; it has no organism semantics. |
| **Conservation** | New pathways could create or duplicate mass. | Every extraction debits a source pool by the exact mass created. Fracture splits mass as `parent - piece`. Combustion and decay move mass into producer detritus. A new lithic ledger (`initial_lithic_kg`) is checked separately from the elemental ledger. Organic objects count toward `human_element_totals`. Tests assert closure. |
| **Computational cost** | The ledger stores the full state every tick. More objects means more memory and deepcopy time. | Natural fragments use compact records whose fixed properties come from a lithology table. Fragment count is bounded per cell. Each agent gets at most three interactions per tick, and affordance enumeration is local. |
| **Replay** | New stochastic outcomes could break determinism. | All draws are SHA-256 of `(actor, target, verb, epoch)`, as `_hunt_succeeds` already does. There is no hidden RNG state. State is JSON-native: string keys, no tuples, no NaN. Checkpoint replay is tested. |
| **Compatibility** | Changing shared functions could alter earlier phases. | Everything is gated by `agentus_capacities_enabled` (default off). With the flag off, the canonical config omits the key, so fingerprints are unchanged. The fresh-carcass pool exists only when the flag adds it. `evolve_humans` keeps its 3-tuple signature, and a new `evolve_agentus_step` returns the consumer state as well. |
| **Experimental interpretation** | Capacity extensions change the model. Results stop being directly comparable to v0. | Model version `capacity-v1` is recorded in the canonical config. v0 (flag off) is re-run on the same seeds in the same session. Ablations isolate diet from manipulation. Seeded knowledge is limited to declared innate priors and is excluded from discovery claims. |

---

## 3. Scope fitted to the roadmap

G10.3 sits after G10.2A (survival affordance substrate) and before any sustainable-survival qualification. It extends G5 (biology), G6 (perception, memory, learning), and G7 (general action) in the live world. Each change is labeled:

- **Implementation repair (R):** declared behavior that was broken or disconnected.
- **Capacity extension (C):** a missing biological or physical possibility.
- **Parameter calibration (P):** changed numbers.

| # | Change | Kind |
|---|---|---|
| R1 | Live manipulation executes in real runs through learned interaction selection, replacing the empty `learned_sequences` gate. The existing wood primitives (`apply_force`, `arrange`, `separate`) become selectable live interactions. | R |
| R2 | `consume` gains a live effect: ingestion from any locally present material, subject to digestibility. | R |
| R3 | Planning uses remembered food locations when the visible patch cannot meet daily need. Memory already stored them; planning ignored them. | R |
| C1 | Omnivorous ingestion: plant tissue, seeds, fresh animal tissue. Wood and decayed tissue are not food. | C |
| C2 | Fresh vs decayed carcass tissue with temperature-dependent spoilage. | C |
| C3 | Capture attempts against live animals: escape, resistance, displacement, injury, removal exactly once. | C |
| C4 | Movable stone fragments with lithology-derived properties; strike, fracture, edge, wear. | C |
| C5 | Fibers from plant tissue, bark, and tendon with source-specific properties; pull apart, twist, interlace, wrap/tighten. Bindings hold or fail under load. | C |
| C6 | Material interactions: edge separates softer material; blunt impact transmits force; binding constrains objects; worn interlaced surfaces moderate cold; fire alters objects. | C |
| C7 | Food-kind and interaction learning with an eligibility trace and bounded, costed exploration. | C |
| P0 | **No existing parameter is changed.** New mechanics introduce new declared constants (section 5). | — |

---

## 4. Mechanics specification

See section 5 (filled in with the implementation).

## 5. Declared abstractions and constants

See implementation notes appended below.

## 6. Pending decisions and known omissions

See implementation notes appended below.
