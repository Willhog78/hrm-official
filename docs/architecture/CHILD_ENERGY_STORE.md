# One energy store for eating, hand-feeding and nursing (2026-10-09)

## Defect

A child's energy was credited against two different bounds:

| Path | Code | Bound |
|---|---|---|
| Eating, hand-feeding | `diet.ingest_pool`, `biology._eat` | the adult `energy_capacity_kcal` |
| Nursing | `biology._provision_dependent` | the size-scaled `energy_capacity_kcal × max(0.10, development_scale)` |

A child aged 2–5 that fed itself could therefore sit above its own store. On its next nursing day the bound cut it back, and the excess energy was erased. This is measured as `child_store_clamp_kcal`:

- second run: 24–29 kcal per nursing day;
- third run: 29–36 kcal per nursing day;
- seed d, third run, year 5 alone: 319,867 kcal.

## Correction (`child_energy_store = "size-scaled-v1"`, default)

This is an isolated accounting fix, scoped by the owner (2026-10-08):

- Eating, hand-feeding and nursing must use one consistent storage capacity.
- Any excess must be explicitly accounted for.
- Size scaling must not be removed merely to make the clamp disappear.
- The world and behavioural incentives stay unchanged.

**What it does:**

1. **One bound.** `biology.energy_store_capacity(profile)` = `energy_capacity_kcal × max(0.10, development_scale)`. Each step it is put on the human's effective profile as `energy_store_capacity_kcal`. Every credit path reads that one key:
   - eating (`ingest_pool`, `_eat`);
   - hand-feeding (`ingest_pool` from the caregiver's hands);
   - nursing (`_provision_dependent`).

   For adults `development_scale` is 1, so their bound is numerically unchanged.
2. **Excess is recorded.** Food a full store cannot take is still eaten: mass and elements move exactly as before, the same as an adult with a full reserve. Its surplus energy is recorded in `humans["energy_store_stats"]["refused_kcal"]`, by age class (`child`, `adult`), not erased.
   - Adults' refused energy is the existing "eaten beyond need" amount. It is now explicit, and adult values do not change.
3. **Nursing removes nothing.** No credit path can lift a child above its store, so the nursing bound never cuts. `child_store_clamp_kcal` stays at 0, and any non-zero value would show a remaining inconsistency.

**Unchanged:**
- Food mass, gut capacity and handling.
- Learned food values. These use the energy offered, not the energy credited.
- Milk, the hand-feeding rule and trigger, adult physiology, and every world rule.

**Behavioural consequence (accepted, not tuned).** Children no longer carry energy above their size-scaled store between nursing days. That is the intended physical consequence of one store.

**Not changed, recorded:** the children's planner judges "hungry" against the adult satiety reference (`biology.py`, the `hungry` lines in the step), while the hand-feeding check uses the size-scaled one. That is a behavioural inconsistency, left for a separate decision.

## Reproducibility

- `unscaled-eating-legacy` (arm suffix `-legacystore`) reproduces the previous build exactly. Checked on seed d over 1,100 days: digest `b3d31d98…` and fingerprint `a6079fe1f306` in both, with the same 76,343 kcal clamp.
- The fingerprint key `agentus_energy_store` is present only when the fix is active (calibrated biology).

## First measurement (seed d, `v1`, 1,100 days)

| | Legacy | Size-scaled |
|---|---|---|
| Child store clamp | 76,343 kcal | 0 |
| Refused, recorded (children) | — | 439,139 kcal |
| Refused, recorded (adults) | — | 4,676,078 kcal |
| Alive at day 1,100 | 20 | 20 |
