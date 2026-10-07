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

### 4.1 State and ownership

| State | Owner | Notes |
|---|---|---|
| `matter.lithic_cells`, `matter.initial_lithic_kg` | Matter | Loose weathered stone seeded at genesis from World `rock_exposure` (`matter/objects.py: seed_natural_fragments`). Fixed bedrock is not extractable. |
| `consumer.carcass_cells[*].fresh_elements_kg` | Consumer | Opt-in (`ecology/animals.py: enable_fresh_tissue`). New deaths enter it; it spoils into the decayed pool. |
| `human.objects` | Agentus | Every handled or derived object (stone, fiber, wood piece, surface, assembly), with `x, y, holder, worn`. |
| `human.capacity_stats` | Agentus | Cumulative counters for reports. No decision reads them. |
| `cognition.food_values / affordance_values / trace` | Agentus | Learned expectations. |

### 4.2 Diet (`human/diet.py`)

| Kind | Source pool | kcal/kg dry | Digestibility | Hand access/day | Notes |
|---|---|---|---|---|---|
| plant tissue | producer `plant_elements_kg` | 2200 (existing) | 0.80 (existing) | unlimited (existing) | Declared innate food. |
| seed | producer `seed_elements_kg` | 3800 | 0.75 | 0.45 kg | Eating seeds removes germination stock: a real ecological cost. |
| fresh animal tissue | consumer `fresh_elements_kg` | 4800 | 0.90 | 0.25 kg + edge bonus | Cutting with an edge adds up to 1.5 kg/day of access. |
| decayed animal tissue | consumer `elements_kg` | 0 | 0 | 0.25 kg | Ingestion harm of 0.6 injury per kg, capped per tick. |
| woody tissue | producer `woody_elements_kg` | 0 | 0 | 0.10 kg | Handling cost only. |

- **Gut capacity.** Total intake per tick is the existing `bite_cap_kg`, shared by all kinds.
- **Excretion.** Unassimilated mass goes to producer detritus in the same cell.
- **Spoilage.** Fresh tissue spoils at 10%/day at ≤4 °C and 55%/day at ≥30 °C, linear in between. Both carcass pools decompose at the existing 5%/tick. Splitting the carcass pool therefore leaves total carcass decay unchanged.
- **Feeding by age.** Infants with full dependence do not ingest. Weaning children eat only the kinds they already value. Only independent agents sample unknown kinds.

### 4.3 Animals

- **Capture.** A capture attempt is a strike or seize on an animal in the agent's own cell. Agents must be at ≥0.5 development scale. Success probability:
  `0.10 + 0.35·capability + min(0.3, impact_J/150) + 0.10·[reach ≥ 0.8 m] + 0.05·edge − 0.6·escape`, clamped to [0.02, 0.85].
  - `escape = 0.15·perception_radius + 0.25·min(1, prey_energy/reproduction_energy)`. A well-fed, perceptive animal is harder to catch.
  - `capability = development_scale × (1 − 0.5·fatigue) × (1 − 0.6·injury)`.
- **Cost of an attempt.** Each attempt costs 60 kcal and 0.05 fatigue. A failed attempt moves the prey one cell away, at the prey's own movement cost. Predators resist: there is a 50% chance of 0.05–0.15 injury.
- **Kills.** `kill_animal` removes the animal from the population exactly once. Its full body enters the fresh-carcass pool and its body water enters carcass water. The death is recorded as `agentus`. The Agentus then eats from the carcass like any other tissue. Leftovers spoil, decompose, or are eaten by other Agentus.

### 4.4 Stone (`matter/objects.py`)

**Lithologies.** Lithology is chosen per cell by deterministic draw, skewed toward harder rock with elevation.

| Lithology | Hardness | Fracture energy (J per kg^(2/3)) | Edge potential | Roughness |
|---|---|---|---|---|
| siliceous_fine | 7 | 20 | 0.90 | 0.15 |
| basaltic | 6 | 45 | 0.45 | 0.35 |
| granitic_coarse | 6 | 70 | 0.15 | 0.70 |
| calcareous_soft | 3 | 14 | 0.25 | 0.50 |

**Natural fragments.**
- 0–4 per cell, in proportion to `rock_exposure`.
- Masses 0.08–4 kg, log-uniform.
- Edges dull (sharpness 0.05–0.20).

**Impact.** Delivered energy is `min(½·m·(v·L)², W·√L)`, where:
- v = 9 m/s × √capability;
- W = 120 J × capability;
- L = 1 + lever/0.7.

Hardness transfer multiplies by `min(1, h_hammer/h_target)` and by a 0.5–1.0 geometry draw.

**Fracture.**
- A fragment fractures if delivered energy reaches `fracture_energy × m^(2/3)`.
- It always yields exactly two pieces, whose masses sum to the parent's.
- **Edges.** Flake sharpness is `edge_potential × (0.25–1.0 draw) × (1 − flake fraction)`, reduced when the strike delivers more than three times the needed energy (crushing). Sharp flakes therefore come mostly from fine-grained rock and are never guaranteed.
- **Hammer.** A stone hammer can fracture too.
- **Injury.** Each strike risks hand injury, more likely when tired or holding an edge. A sharp flake carries a flying-chip risk.

**Cutting.**
- Capacity is `sharpness × min(1, h_edge/(1.5·h_target)) × capability`.
- A blunt stone transmits impact but does not cut.
- Each use dulls the edge, faster on harder targets.

**Heat.** Applies to stones lying in fire:
- Strong fire (intensity ≥ 0.6) can crack them, with mass conserved and no worked edge.
- Moderate fire (0.2–0.6) marks fine siliceous stone as heat-altered, raising its later edge potential by 15%.

### 4.5 Fibers and binding

**Fiber sources.**

| Source | Length (m) | Thickness (mm) | Flexibility | Strength (MPa) | Friction | Wet effect |
|---|---|---|---|---|---|---|
| plant tissue | 0.15–0.7 | 0.6–1.5 | 0.85 | 60 | 0.45 | +10% |
| bark (woody pool) | 0.3–1.4 | 1.0–3.0 | 0.55 | 45 | 0.60 | −25% |
| tendon (fresh carcass) | 0.05–0.25 | 0.8–2.0 | 0.75 | 90 | 0.35 | −60% |

**Extraction.**
- Every extracted strand debits its exact mass from the source pool.
- Plant strands come free by hand.
- Bark and tendon come out shorter without an edge, and a tendon rarely comes free intact by hand.

**Manipulations.**
- **Pull apart:** splits one strand into two, with mass conserved.
- **Twist:** merges strands. Length shortens by 10%. Load sharing depends on friction (efficiency 0.55–0.90). A stiff strand (flexibility below 0.3) cracks instead.
- **Interlace:** four or more strands form a surface. Its area follows strand lengths and spacing. Low-friction strands do not hold the pattern and unravel.
- **Wrap and tighten (bind):**
  - Pull tension is 250 N × capability × (0.4–1.0 draw).
  - Pulling beyond the strand's strength breaks it.
  - A strand shorter than 1.2 turns around the parts cannot bind them.
  - Bending a thick, stiff strand around a small radius cracks it.
  - The resulting hold is `T·(e^{2πμ·wraps} − 1)`, capped at twice the binder's strength.

**What a binding changes.**
- The bound parts occupy one hand slot.
- Striking with a bound head on a stick uses the stick as a lever, delivering more impact energy.
- Each strike passes a load of `E/0.02 m × 0.05` through the binding:
  - above the hold, the parts slip apart, one stays in hand and the rest fall;
  - above twice the strand's strength, the binder breaks.
- Wetting weakens moisture-sensitive binders.

**Surfaces worn on the body.** A worn surface raises effective ambient temperature in cold by up to 8 °C × min(1, area·cohesion/1.8 m²).

**Decay and fire.**
- Organic objects decay into producer detritus at 0.2%/day when held and 0.5%/day when lying on the ground.
- On the ground they also burn in fire at 10% × intensity per tick. Strand integrity falls with decay.

### 4.6 Perception, choice and learning (`human/perception.py`, `planning.py`, `interactions.py`)

**Perception.**
- Cells are the agent's own and its orthogonal neighbours (unchanged).
- New fields per cell: seed, fresh and decayed tissue mass, animal kinds present, loose-stone count.
- `expected_food_kg` is the visible mass of each kind, capped at a day's hand access and weighted by the agent's own learned value relative to its innate plant reference. A kind the agent has never valued counts as zero.

**Planning.**
- Planning uses `expected_food_kg`.
- When the visible patch cannot meet daily need, a hungry agent steps toward the nearest place in its own memory that held enough food. Memory is forgotten after 96 days and may be stale.
- Otherwise the existing least-visited exploration applies.

**Interactions.**
- Up to three per tick. None for agents still dependent on a caregiver or with fatigue above 0.8.
- Options are enumerated from physical presence only.
- Choice: explore an untried option with probability 0.25 when hungry or 0.08 otherwise; otherwise take the best option with positive learned value; with probability 0.03, retry a known non-positive option.

**Learning.**
- Reward = (attributable food gain − effort) / basal − 2 × injury.
- Gains from eating fresh tissue are attributed to the kill and to any cutting that raised access.
- A three-step eligibility trace, decay 0.5, passes positive gains back to earlier interactions.
- Food values learn from net experienced kcal per kg, including harm. The first experience sets the value.

**Hands and carrying.** At most 2 rigid objects, 6 soft objects, and a 20 kg load × development scale. Held objects travel with the agent. On death they drop where the agent died.

**Existing wood primitives.** `apply_force`, `arrange` and `separate` from G7 are offered as live interactions, so the arranged-material exposure effect from G10.2A can now be reached in live runs.

## 5. Conservation ledgers: what they do and do not prove

- **Element ledger.** Matter cells + producer pools + consumer bodies and carcasses + Agentus bodies, remains and objects = Matter initial elements. This is checked by the G5 combined check and the G10.3 tests.
- **Water ledger.** Unchanged.
- **Lithic ledger.** Natural fragments + stone in Agentus objects = `initial_lithic_kg`.
- **Energy (kcal) is a metabolic account, not a conserved quantity.** Food energy is derived from ingested tracked mass through declared densities. It is not debited from a world energy store. Solar input to plants is not converted into these food calories.
- **What the ledgers do not show.** They show that tracked mass is neither created nor duplicated. They do not show biological realism: tracked elements are six biological elements plus lithic mass; tissue composition is not distinguished; protein, fat, vitamins and toxins are not modeled.

## 6. Known omissions and pending decisions

**Absent food sources.** Roots and tubers, fruit, insects, eggs, aquatic food, honey, and bone marrow have no substrate. Agentus remains are not food (by design).

**Animal scale (pending decision, not changed).** The consumer ecology is not scaled with `material_scale_factor`. In the experiment world, live animal tissue totals well under one Agentus-day of energy. The animal-food pathway works, but it cannot materially affect survival until a separately authorized calibration changes animal abundance or body size.

**Not modeled:**
- scavenging by predators (only decomposition and Agentus compete with each other for carcasses);
- throwing, ranged hunting, traps, and chasing across cells;
- carrying food or water;
- containers;
- heat changing food;
- fire made or controlled by Agentus;
- bone and horn as materials;
- quarrying of fixed bedrock.

**Learning limits.**
- Values are keyed by perceivable classes, not by individual objects.
- No social learning of food or interactions: the existing `signal`/`imitate` path is still not invoked in live runs.
- Credit assignment is a short trace; long setup chains, such as gathering strands to later bind a head on a stick, earn credit only if a food gain follows within three interactions.

**Thirst.** The planner still has no thirst signal (finding from the plant-lifecycle diagnosis). Dehydration deaths in these runs reflect that planner limit, not water scarcity.
