# Conditional sequence valuation — stage 2

## Purpose and boundary

Owner authorized continuation after stage 1 on 2026-10-09. This is an opt-in
extension of PR #41, not a replacement for the cognition or physical kernels.
No AGENTS.md exists in this checkout. Causal ownership, the current roadmap,
production configuration builder, transition contract, interaction learning and
physiology were inspected before editing.

The new model can prefer a preparatory action with a negative individual value
because its experienced continuation has a positive expected net value. Every
selected step still executes through the existing physical guards and transaction.
There is no shared skill library, inherited recipe, semantic LLM descriptor,
observer-fed knowledge, named shelter outcome or material reward.

## Pre-edit risks and implementation surface

The assessment identified duplicate food credit, correlation mistaken for causal
preparation, missing cover-benefit attribution, combinatorial search, stale plans,
and regression of existing modes. The coordinated changes are confined to:

- `human/transitions.py`: experienced benefit and bounded conditional evaluation;
- `human/interactions.py`: local/body state cues, conservative food attribution,
  discretionary exploration and live selection, terminal thermal credit;
- `human/biology.py`: read-only marginal thermal measurements and callback wiring;
- `config.py`: explicit version and compatible energy-accounting validation;
- `qualification/genesis/tier_observer.py`: experimental arms and read-only checks.

Existing geometry, material sources, heat coefficients, resource quantities,
physical action costs, destination planning, deployment settings, ports and
runtime environment handling are unchanged.

## Versioning

`agentus_transition_model` now also accepts `experienced-transitions-v2`.
`none` remains the default. `experienced-transitions-v1` remains write-only.
V2 requires capacities and `child_energy_store="size-scaled-v1"`, so ingestion
reports refused energy rather than mistaking it for an experienced gain. Existing
fingerprints omit `none`; checkpoints cannot be silently converted to another
version.

Qualification arms `v1-transitionsv1` and `v1-transitionsv2` select these versions.
For example:

```bash
PYTHONPATH=src:. python -m qualification.genesis.tiers smoke --arm v1-transitionsv2
```

This is an experiment configuration; no production runner or Railway service
was switched to it.

## Conditional state and prediction

V2 retains v1's local physical projection and adds coarse own energy, hydration,
fatigue and injury cues plus the amount made accessible during this tick. The
latter distinguishes an initial useful cut from a redundant third cut. Weather
and position remain part of the state. No distant state or peer body/memory is read.

The planner groups outcomes by experienced before-state and action. It evaluates
at most three actions, never repeats an action within one imagined path, and
limits search to 128 state expansions. A continuation requires both an exact
match to the remembered after-state and an action newly enabled by that transition.
This conservative rule rejects a time-near action whose useful successor was
already possible. It is not a complete causal model: coarse state aliasing and
unrepresented dependencies remain limitations.

Each action needs at least two experiences in that state before being ranked.
Two additional unknown adverse outcomes shrink expected benefit, while actual
effort and injury costs remain fully charged. Successful and failed outcomes
retain separate counts and contribute to the same conditional expectation.
Future net value is discounted by 0.9 per continuation. Real subsequent failures
can extinguish a formerly positive prediction.

Live choice considers only currently offered physical options. It recomputes
after every step, preserving the three-interactions-per-tick limit. A speculative
plan requires at least two basal-energy days and two water-loss days above the
lethal hydration floor. The existing destination/biological priorities remain.
No remembered after-state is ever applied directly to the world.

## Costed exploration

One expensive preparation experience can otherwise suppress its own retesting
before the useful continuation is discovered. Under adequate reserves, v2 gives
an experienced state change that opened new actions a 0.12 chance of another
costed trial, with a budget of eight attempts in that condition. A single paid
but insufficiently repeated downstream experience permits further testing up
to sixteen preparatory attempts. These attempts receive no novelty reward.
Ordinary exploration and physical costs still apply. The bounds are engineering
assumptions, not experimentally calibrated human learning parameters.

## Benefit attribution

Food credit uses net energy actually received: assimilable energy minus refused
energy and handling cost. A cut receives only intake beyond hand access, in
physical action order; a redundant later cut receives zero. A capture receives
only intake beyond the fresh material present before that capture. Overlapping
capture and cut routes share one bounded received-food budget. V2 does not send
this gain backward through the old temporal eligibility trace.

Thermal credit requires an actual own wear or arrange event in that tick. The
readout isolates the new material's marginal contribution, comparing against
that individual's pre-interaction local arrangement/worn state under the same
current terrain, position, weather and actual skin wetness. A tiny addition
cannot claim preexisting cover or clothing's total benefit. If both change near
a thermal-cost cap, their readouts share a single combined energy-saving budget.
These readouts change no energy, water, injury, geometry or material state.

Declared perceptual abstraction: reduced thermal energy expenditure represents
experienced bodily benefit. The agent does not receive a weather forecast,
construction goal or physics counterfactual as a planning state. Rain/wetness,
water savings and injury reductions are not independently rewarded here.

Only the terminal edge receives direct benefit. Preparatory value comes from
conditional continuation, not a second copy of the same reward. Meal and heat
callbacks cannot settle the same context twice. Passive later occupancy, another
individual's construction, failed wearing and shape change without benefit do
not generate action credit.

## Verification

210 distinct tests passed: 153 micro tests, two V2 integration tests, four
transition-memory tests, three observer tests and 48 selected existing
regressions. Coverage includes adverse outcomes, urgent needs, duplicate reward
settlement, material availability, marginal thermal attribution and exact
checkpoint replay.

The fast qualification tier passed, including the default three-seed, 75-day
smoke checks. The V2 smoke arm also passed all three seeds for 75 days with no
failures or warnings. Observed and unobserved ledger digests matched; maximum
relative element error was approximately 1.21e-15, and no individual exceeded
three interactions per tick.

In 300 controlled opportunities, the unpatched chooser first completed
grasp→cut at opportunity 246, completed 55 chains in total, and made 53
value-driven grasp choices and 53 value-driven cut choices. Grasp retained a
negative standalone learned value. No action sequence was supplied to the
chooser. In contrast, the normal 75-day V2 ecology produced no value-driven
sequence choices in any seed. These results establish conditional sequence
selection in the controlled fixture, not autonomous ecological discovery.

Full-repository tests and long-run survival qualification were not run. The
machine-readable smoke and controlled-fixture summary is in
`experiments/genesis/summaries/SEQUENCE_VALUATION_V2_2026-10-09.json`.

## Evidence limits and next work

Controlled fixtures supply known material/food and repeated opportunities;
they are not an autonomous ecology or evidence of tool manufacture. Positive
sequence selection in those fixtures does not establish shelter invention,
useful autonomous weaving, population-level transmission or cultural persistence.

Thermal credit currently measures the first tick after a manipulation. Benefits
accumulating over many later days are not amortized into the originating sequence.
Longer procedure continuity and delayed thermal returns require their own
provenance and tests before sequential imitation. A three-action planning depth
is a bounded initial search horizon, not a permanent limit on learned procedures.

The current 0.25 kg force/arrange fixture produces only about 0.00113 kcal of
cold-energy savings against approximately 21.75 kcal of combined effort. The
model correctly treats that short procedure as costly. The physical/action
substrate and longer-term payoff problem are not solved by raising its reward.
