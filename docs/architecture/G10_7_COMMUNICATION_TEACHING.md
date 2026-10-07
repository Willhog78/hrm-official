# G10.7 — Communication and teaching (design opening)

**Status: design question, not implemented.**

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

## 4. Proposed first slice (G10.7a)

1. **Close the leaks** (versioned; old behaviour reproducible behind a flag):
   - `observe_outcome` transmits the visible event (verb, object classes, visible result), and the observer appraises the result with its own values;
   - `observe_food` raises the observer's tendency to *taste* that kind, rather than copying the eater's energy yield;
   - G7 `signal_sequence` is quarantined as non-physical: kept for the G7 gate record, unusable in live runs.
2. **Observation record.** Each agent keeps a bounded memory of perceived events, `(epoch, actor id, verb, object classes, visible result)`. This becomes the substrate for imitation: the learner may try the observed verb on the observed object classes and is rewarded only by the world.
3. **Following.** Proximity to a conspecific can be valued from experience (the agent arrived somewhere good after following). There is no innate "follow" rule beyond what dependents already do.
4. **One costly call** with no content: emitted on strong arousal, with physical range, energy cost and detectability by animals. Receivers learn what follows it.
5. **Measures** for the existing tiers:
   - how each value was acquired (own trial, observation, or provisioned taste);
   - transmission chains (who acquired a practice from whom, across generations);
   - persistence of practices across individuals;
   - call–event contingency, and receiver responses.

**Gate for G10.7a**, under the advancement rule (no survival requirement):
- micro tests show that nothing non-physical travels;
- each channel works only within range and at a cost;
- smoke and diagnostic integrity hold;
- the diagnostic reports the measures above.

Whether transmitted practice actually persists is the experiment that comes after.
