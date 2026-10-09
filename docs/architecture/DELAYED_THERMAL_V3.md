# Delayed experienced thermal returns — stage 3

The owner authorized continuation from draft PR #42. The pre-edit assessment
identified stale material provenance, credit to another individual's protection,
overlapping claims, duplicate daily settlement, unbounded memory and regressions
of existing modes. The implementation adds an explicit V3 mode, bounded physical
attribution records and live physiology settlement. It does not change thermal
coefficients, action costs, material quantities, destination planning, deployment
configuration, ports or environment handling.

## Mode and boundaries

`agentus_transition_model="experienced-transitions-v3"` retains V2's bounded
conditional planning and received-food attribution. `none`, V1 and V2 retain
their existing behavior. V3 requires capacities and size-scaled energy accounting;
its checkpoint fingerprint cannot be silently converted to V2. The qualification
arm is `v1-transitionsv3`. No production runner was switched to it.

## Physical attribution

An individual has at most two active `thermal_trials`: one for worn material and
one for an arrangement. These are backend physical attribution records on the
individual's state, outside cognition and outside its perceptual projection.
They contain originating transition IDs, actual material provenance, the original
basal-energy normalization and the starting tick. No peer memory, global skill
library, semantic label, recipe or predicted world state is introduced.

Only an actual own wear/arrange change starts a trial. Unrewarded preparations
receive no direct reward; their value still comes from experienced conditional
continuation. A new overlapping manipulation supersedes that kind of trial and
uses the immediately preceding state as its baseline. It cannot restart credit
for an older contribution or take credit for preexisting protection.

Each later physiology step measures the current marginal thermal-energy saving,
under actual local weather, fire, terrain, position and skin wetness. The existing
shared budget prevents worn and arranged claims from jointly exceeding the
combined saving, including at the thermal cap. Attribution changes no physical
energy, water, injury or material result. Rain/wetness savings and avoided injury
are not separately rewarded.

Worn provenance follows exact worn-object IDs. Losing, transferring or changing
the worn set ends the trial. The readout removes only the credited newly worn
IDs from today's inventory; current area/cohesion therefore determines today's
saving. Material decay lowers the return rather than freezing original warmth.

Arrangement provenance requires the same cell, exact arranged mass/geometry and
unchanged intervention revision. V3 physical execution increments that local
revision whenever arranged mass or geometry changes. An intervention invalidates
the older trial even if a later act restores the original shape. Leaving the
cell, decomposition or another individual's modification ends credit. Position
within the cell remains an actual readout input, so being outside the protective
geometry provides no invented benefit. A passive occupant has no trial to credit.

Trials end after 32 ticks, or when their originating transition is forgotten.
Each day's realized gain is discounted by `0.97 ** age`, divided by the originating
basal energy and shared among that trial's actual terminal attempts. Attempt
counts remain physical action counts; passive days do not manufacture additional
trials. One persisted settlement epoch prevents duplicate credit across contexts
or checkpoint continuation. Removed individuals take their trials with them;
newborn construction does not inherit these records.

The horizon and discount are bounded engineering assumptions, not calibrated
claims about human learning. Exact provenance deliberately undercredits modified
or later revisited structures. V3 does not amortize an unlimited lifetime of
benefits or solve credit for multi-person construction.

## Evidence

The controlled fixture supplies a 0.015 m² surface at 0°C. Its first-tick thermal
saving is 0.6 kcal, below the 4 kcal wear cost. Eight controlled grasp/wear trials,
each followed by 32 actual thermal physiology steps, produce a discounted return
of approximately 12.45 kcal per wearing attempt. Conditional grasp value becomes
positive, although grasp's direct value remains negative. The real chooser then
selects grasp from currently offered options. These trials explicitly arrange
the training actions; they prove delayed valuation, not spontaneous invention.
They isolate thermal physiology; ordinary basal feeding and movement are outside
that fixture. A separate live-biology test verifies actual settlement and exact
state replay after JSON serialization with an active trial.

All 11 new micro tests pass. They cover discount, real physical equivalence,
duplicate settlement, expiry, forgotten origin, transfer, decay, changed weather,
leaving a structure, intervention, passive occupancy, overlap, cognition isolation
and live-biology continuation. Two new integration tests verify exact weather
checkpoint replay and mode/accounting boundaries.

The default fast tier and V3 smoke each pass three seeds × 75 days with zero
failures/warnings. Observed/unobserved ledger digests match. V3's maximum relative
element error is approximately 1.21e-15; the three-interactions-per-tick limit
holds. All three normal V3 worlds have zero value-driven sequence choices.

223 distinct tests passed: 164 micro tests and 59 selected existing/new integration
and regression tests. Full-repository tests and long-run survival qualification
were not run. Machine-readable results:
`experiments/genesis/summaries/DELAYED_THERMAL_V3_2026-10-09.json`.

## Remaining gap

The existing 0.25 kg wood arrangement's approximately 0.00113 kcal first-tick
saving remains far below its approximately 21.75 kcal combined preparation cost,
even across this horizon. Delayed credit must not make an uneconomical physical
procedure attractive. Longer procedure continuity, repeated material accumulation
and measured autonomous ecological opportunities remain separate work before
sequential imitation. No shelter invention or cultural transmission is demonstrated.
