# G10.7 — Communication and teaching (design opening)

**Status:** design opening. G10.7a step 1 (leak closure) is merged (PR #29); step 2 (witnessed-event memory) is implemented. See sections 5 and 6.

The first question: what primitive information can one Agentus physically signal or demonstrate to another, without handing over language, concepts or named techniques?

The rule this design follows: **information may only travel through something a body emits or the world displays, and a receiver may only get what its own senses register.** Meaning is never transmitted. It is built by the receiver's own learning, from what follows the percept.

## 1. What exists today, and where it breaks that rule

| Mechanism | What travels | Physical? |
|---|---|---|
| G7 `communication.signal_sequence` / `imitate_signal` | The sender's primitive action recipe (for example `grasp, carry, arrange`) is written straight into the receiver's `learned_sequences`. | **No.** There is no channel, range, cost or perception, so it is telepathic recipe transfer. It is only used by the G7 gate and test, never in live runs. |
| G10.4 `observe_outcome` | The actor's **internal reward value** for an affordance key, written into the observer's value table. | **Partly.** The act is visible. The reward is an internal quantity no observer can see. |
| G10.4 `observe_food` | The eater's **assimilated kcal/kg** becomes the observer's prior. | **Partly.** That something was eaten without visible harm is observable. Its energy yield is not. |
| `perceive_local` → `recognized` | The ids of conspecifics within one cell. | Yes, apart from the id being a label; it stands in for recognition. |
| Caregiver nursing | Matter and energy move from caregiver to child. | Yes. |

These leaks must be closed before teaching is built on top of them. Otherwise any "transmission" result could just be the shortcut at work.

## 2. Primitive information a body can carry

These are ordered from least to most assumed. Each gives the physical carrier, what the receiver perceives, and what stays private.

1. **Presence and position.**
   - *Carrier:* the body itself.
   - *Perceived:* a conspecific is here or adjacent, and over days, where it goes.
   - *Private:* why it went there.
   - *Effect:* following others is enough for local enhancement. A naive agent that tracks a provisioned one ends up at its water and food, with nothing told. This already exists in principle; nothing reinforces following yet.
2. **Visible body state.**
   - *Carrier:* the body: injury, emaciation, age and size, sex, carried or worn objects.
   - *Perceived:* coarse classes ("injured", "thin", "carrying a stone").
   - *Private:* energy, water, values and memories.
3. **Performed action.** This is demonstration.
   - *Carrier:* the movement itself, observable to anyone in the same cell.
   - *Perceived:* the verb, the object classes involved and the tool held, for example "strikes small stone on large stone".
   - *Private:* intent, effort cost, reward and the action's history.
4. **Visible result.**
   - *Carrier:* changed matter.
   - *Perceived:* what changed: a flake appears, a carcass is opened, an animal stops moving, food is taken in, the actor flinches (injury rises).
   - *Private:* energy gained.
   - *Effect:* the observer judges the result with its **own** values. Seeing meat produced matters only to an observer that values meat. That is how real value can transmit without the actor's numbers.
5. **Artefacts left in the world** (stigmergy).
   - *Carrier:* objects that persist: flakes, bindings, worn surfaces, opened carcasses.
   - *Perceived:* the object and its physical properties when encountered.
   - *Effect:* this already happens. A flake lying by a carcass draws attention to both without any agent present.
6. **Transferred material.**
   - *Carrier:* food, an object or a tool physically handed over, with mass conserved.
   - *Perceived:* the received thing itself.
   - *Effect:* a child given a food kind tastes it, so it learns the kind through its own ingestion. Information rides on matter.
7. **Emitted signal** (a call or gesture).
   - *Carrier:* a sound or movement with a physical range, an energy cost and an intensity. It is also detectable by prey and predators, which keeps it costly.
   - *Perceived:* "a call of intensity *i* from that direction". There is **no content field**.
   - *Effect:* the receiver learns what tends to follow the call (a predator, food, a caregiver) by its own association.
   - *Innate part:* the only innate element is that strong arousal (pain, a predator charge, separation of a dependent) produces a call. This is a declared reflex, like the thirst interoception. How the receiver *responds* must be learned.

**What must never travel:**
- action recipes as symbols, or affordance keys as labels;
- reward or value numbers, or energy yields;
- remembered coordinates, except by physically leading someone there;
- food kinds as names;
- anything named (a technique, tool type or practice).

## 3. Teaching without a teaching module

Teaching is defined by behaviour (Caro & Hauser, 1992):
- the demonstrator modifies its behaviour only when a naive individual is present;
- at a cost to itself;
- so that the learner acquires faster than it would alone.

Under that definition, teaching cannot be granted. It has to be *measured* and must emerge, for example a caregiver that performs a valued action more often while its dependent is co-located. That needs a learnable reason, such as the caregiver's own fitness interest through the child, which takes generational depth. The first slice therefore provides channels and measures. Teaching is a later question, not a feature.

## 4. G10.7a plan (owner decision, 2026-10-07)

The order is leak closure → perceptual event memory → imitation → following → measurement.

**No call yet.** A call would open a new channel whose meaning could quietly become hard-coded. G10.7a must first show that visible action, visible consequence and imitation work without any symbolic signal. The costly call (section 2, item 7) is G10.7b.


1. **Close the leaks** (versioned; old behaviour reproducible behind a flag):
   - `observe_outcome` transmits the visible event (verb, object classes, visible result), and the observer appraises the result with its own values;
   - `observe_food` raises the observer's tendency to *taste* that kind, rather than copying the eater's energy yield;
   - G7 `signal_sequence` is quarantined as non-physical: kept for the G7 gate record, unusable in live runs.
2. **Observation record.** Each agent keeps a bounded memory of perceived events, `(epoch, actor id, verb, object classes, visible result)`. This becomes the substrate for imitation: the learner may try the observed verb on the observed object classes and is rewarded only by the world.
3. **Following.** Proximity to a conspecific can be valued from experience (the agent arrived somewhere good after following). There is no innate "follow" rule beyond what dependents already do.
4. **Measures** for the existing tiers:
   - how each value was acquired (own trial, observation, or provisioned taste);
   - transmission chains (who acquired a practice from whom, across generations);
   - persistence of practices across individuals;

**Gate for G10.7a**, under the advancement rule (no survival requirement):
- micro tests show that nothing non-physical travels;
- each channel works only within range and at a cost;
- smoke and diagnostic integrity hold;
- the diagnostic reports the measures above.

Whether transmitted practice actually persists is the experiment that comes after.

## 5. G10.7a step 1 — leak closure (implemented)

**Flag.** `agentus_observation_model`:
- `visible-v1` is the default and is recorded in the canonical config when capacities are on.
- `g10.4-legacy` reproduces G10.4 exactly: same fingerprints and ledger digests as pre-G10.7 `main`, checked on seeds a and c over 60 days.
- The diagnostic arm suffix for legacy is `-g104obs`.

**1. G7 recipe transfer.**
- `signal_sequence` and `imitate_signal` refuse to run unless called with `compatibility="g7-legacy"`.
- Only the G7 gate and the G7 test pass that flag.
- A micro test fails if any live module references the recipe channel.

**2. `observe_outcome`.** An observer in the same cell sees the act and its visible consequence:
- food the actor then ate because of it (kind and kg, not energy);
- the classes of objects that appeared;
- the actor being hurt.

The observer appraises this with **its own** history:
- its own value per kg of that food, if it has eaten that food;
- its own best value from acts using the appeared class as a tool;
- minus twice the visible injury.

With no relevant history, nothing is learned. The actor's reward and effort never travel.

**3. `observe_food`.** An observer records only `{kind: {harmless, harmful}}` sightings, where "harmful" means visible distress (ingestion hazard).
- **Seen eaten harmlessly:** the agent tastes that kind at probability 0.5 when it is present and the agent feeds itself.
- **Seen harmful more often than harmless:** the agent never tastes it.

No food value is set. The value comes only from the observer's own ingestion (`food_learned_after_observation` counts this path).

**Evidence (fast loop).**
- **Micro:** 11 new social tests; all micro tests pass. Among them:
  - an observer never receives reward;
  - two observers appraise the same event by their own food values, whatever the actor's reward;
  - visible injury teaches caution;
  - an appearing object matters only to an observer that has used such objects;
  - nothing travels across cells;
  - seeing food eaten transfers no value;
  - tasting likelihood rises when food is seen eaten safely and falls to zero when distress is seen;
  - value comes only from eating;
  - the G7 path is unavailable without its flag;
  - the legacy behaviour reproduces with its flag.
- **Smoke:** 0 fail, 0 warn.
- **Diagnostic `observation`** (`v1-g104obs` vs `v1`, 4 seeds × 180 days):

  | Measure | Legacy | visible-v1 |
  |---|---|---|
  | Legacy food adoptions | 11 | 0 |
  | Living agents valuing seed | 42 | 32 |
  | Observed ingestions recorded | — | 2,657 |
  | Foods learned by eating after observing | — | 0 |
  | Affordance transmissions (own appraisal) | — | 3 (`break:woody|none`) |

  - The 10 who do not value seed are dependents. They saw seed eaten up to 115 times and will be ready to taste it once they feed themselves. Under legacy, the same infants had been handed an energy value for seed.
  - Survival, interactions and intake are unchanged.
- **Gates and suite:** all 19 gate scripts pass, including G7 on its legacy path. The full pytest suite passes.

**Note on G7's exit condition.** G7's "transmitted to another agent which reproduces the effect by imitation" was satisfied only through the non-physical recipe path. That claim is reopened: G10.7a steps 2–3 (perceptual event memory, imitation) must earn it physically.

## 6. G10.7a step 2 — witnessed-event memory (implemented; perception → memory only)

**Flag.** `agentus_event_memory_enabled` is default on. It is active only with capacities and a visible observation model, and is recorded as `agentus_event_memory: "witnessed-v1"`. The diagnostic arm suffix `-nomem` turns it off.

**What is stored.** Every agent in the same cell as an act or a meal, dependents included, appends one event to `cognition["witnessed"]`:
- `epoch`;
- `actor`: the recognised individual, which is the id used by `perceive_local`;
- `act`: the verb and object classes, for example `strike:stone_small|stone_heavy` or `eat:seed`;
- `created`: classes of objects that appeared;
- `eaten_kg`: the food kind and amount visibly eaten as a result;
- `hurt`: visible injury or distress.

The memory keeps the newest `WITNESSED_MEMORY = 32` events (a declared bound). The actor's reward, effort, values and history are never stored. Agents do not witness their own acts; those are in `trace`.

**Write-only.** No decision reads the memory. Two checks enforce this:
- **Code-level guard:** a micro test fails if any source line other than the single writer references `"witnessed"`.
- **Run-level check:** `test_g10_7_memory_non_causal.py` runs a production seed for 40 days with memory on and off. Every authority's state is identical once the memory field and its counters are removed.

**Evidence.**
- **Micro:** 8 new memory tests; all 74 micro tests pass.
- **Smoke:** 0 fail, 0 warn. Results are identical to before step 2.
- **Diagnostic `memory`** (`v1-nomem` vs `v1`, 4 seeds × 180 days): every outcome measure is identical. That covers survival, deaths, interactions, intake, hunting, learned values and transmissions.
- **Gates and suite:** all 19 gate scripts and the full pytest suite pass.

**What the memory holds** (findings that bear on imitation):

| Measure (per seed, day 180) | Range |
|---|---|
| Events witnessed | 563–814 |
| Share that are eating (plant, seed) | about 95% |
| Agents holding memories | 7–11 |
| Events held per agent | 22–25 of 32 |
| Distinct acts per agent | 2.6–3.2 |
| Distinct actors per agent | 1.0–1.5 |
| Non-eating events still held | 4–13 |
| Dependents with memories | 1–3 |

- **Observation is socially sparse.** Most agents only ever see one other individual act. Co-location is rare outside caregiver and child pairs.
- **Eating crowds out manipulation.** With a plain newest-32 bound, witnessed manipulative acts are flushed within days by the steady stream of witnessed meals. Imitation built on this memory would rarely have a manipulative act to draw on.

  This is a design question for step 3, not a defect to tune here. The options are:
  - a separate bound per event class;
  - retention by visible consequence (an act that produced an object or a meal stays longer);
  - leaving it as is and reporting it.
