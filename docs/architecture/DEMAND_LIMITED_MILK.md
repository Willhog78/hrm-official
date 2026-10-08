# Demand-limited milk (2026-10-08)

**Owner decision.** Authorize demand-limited milk transfer:
- Determine what each child can receive before any milk is produced.
- Charge the mother for the amount actually produced, including the stated conversion cost.
- If milk is produced but not absorbed, account for where it goes; do not erase the difference.

This removes payment for milk a child cannot use. It does not guarantee a mother enough energy to nurse three or four children, and no weaning age, nursing amount, or physiology value is changed.

## 1. The demonstrated problem

`_provision_dependent` (supply-capped, now `nursing_model = "supply-capped-legacy"`):
1. charged the mother `min(nursing_energy_kcal_per_tick × nursing_factor, her reserve above one day of basal)`;
2. added that to the child's energy;
3. then capped the child's energy at its size-scaled store (`energy_capacity_kcal × development_scale`).

The amount above the cap was silently erased. Over the 5-year daily world:

| Seed | Mothers paid (kcal/day) | Children absorbed (kcal/day) |
|---|---|---|
| a | 806 | 230 |
| b | 392 | 141 |

On seed b's days when mothers were short of reserves, they paid 765 and children absorbed 129.

## 2. The change (`nursing_model = "demand-limited-v1"`, default)

All of this happens on the child's turn, in the same place in the step as before:

1. **Child's room.** `room = child store capacity − child energy`. It is fixed before any milk is made.
2. **Supply.** The supply is exactly as before:
   - `reference-v1`: up to `350 × nursing_factor`, from the mother's reserve above one day of basal.
   - `reference-v2`: tapered by her reserve, with efficiency 0.8.
3. **Produced** = `min(supply, room)`.
4. **Charged to the mother** = `produced / efficiency`.
   - `reference-v1` states no conversion loss, so the efficiency is 1.
   - `reference-v2` states 0.8. The difference, `cost − produced`, is recorded as conversion heat: an explicit loss, not an erasure.
5. **Child.** The child's energy becomes `min(capacity, before + produced)`, the same expression as before. Because production is limited to the room, nothing produced is cut.
   - `milk_unabsorbed_kcal` records any gap. It is zero by construction, and it is recorded so that a gap would be visible.
6. **Water and dry mass.** These were already limited by the child's need, so they are unchanged.

**What the child receives is unchanged.** Every day, the child gets exactly what it got before. The only difference is what the mother pays. The micro tests check this against the legacy path.

**Pre-existing defect, kept visible.** A child whose energy is already above its size-scaled store, from food it found itself, is cut back to the store on a nursing day, exactly as before. This is not milk. It is recorded as `child_store_clamp_kcal`. The defect (the child's store is not size-scaled when the child eats) was flagged in `CAREGIVING_SOLID_FOOD.md` and is still open.

## 3. Accounting

`humans["nursing_stats"]` holds totals, in kcal unless stated:
- `nursing_days`, `nursing_days_demand_limited`;
- `milk_supply_kcal`: what the supply cap would have drawn;
- `milk_produced_kcal`, `milk_cost_kcal`, `milk_conversion_heat_kcal`;
- `milk_absorbed_kcal`, `milk_unabsorbed_kcal`;
- `child_store_clamp_kcal`.

These identities hold:
- `cost = produced + heat`;
- `produced = absorbed + unabsorbed`.

`budget_audit` prints them per nursing day.

## 4. Reproducibility

- `supply-capped-legacy` reproduces the previous commit's ledger digest and fingerprint exactly. Checked on seed a, 500 days: `17d569a8…` in both.
- The fingerprint key `agentus_nursing` is present only when demand-limited milk is active, which requires calibrated biology.
- Arm suffix `-legacymilk` selects the legacy model in `tier_observer.build_config`.

## 5. First measurement (seed a, `v1`, first 500 days)

| | Supply-capped | Demand-limited |
|---|---|---|
| Milk the mothers paid for | 486,150 kcal | 288,283 kcal |
| Milk children absorbed | 288,283 kcal | 288,283 kcal |
| Unabsorbed | erased (not recorded) | 0 |

- The limit applied on 1,325 of 1,389 nursing days.
- After the first 500 days the two runs diverge, because the mothers now hold more reserve.

## 6. What this does not change

- Nursing amounts, the dependence curve, weaning, physiology defaults and birth spacing.
- The solid-food rule.
- Milk still has priority: it is given before the child's own foraging and before any hand-feeding. Whether milk keeps children above the hand-feeding trigger is measured by the audit's hand-feeding checks. It is a hypothesis, not a finding.

## 7. Open defect, recorded for an isolated correction: the child energy clamp

**Not part of the milk change, and not to be bundled with plant or water changes.**

- **Where.** `_provision_dependent` ends with `child.energy = min(child capacity, before + milk)`, where child capacity = `energy_capacity_kcal × development_scale`. `ingest` caps any eater at the adult `energy_capacity_kcal`. A child aged 2–5 who feeds itself can therefore sit above its size-scaled store. On its next nursing day the `min` cuts it back, and the excess energy is erased.
- **Measured** (second daily-world run, `nursing_stats.child_store_clamp_kcal`):
  - 24–29 kcal per nursing day across the four seeds;
  - zero in years 1–2;
  - seed a rises from 36,383 kcal in year 3 to 189,744 kcal in year 5.
- **Correction to decide:** one store bound for children, applied wherever energy is credited (eating, hand-feeding and milk). Either:
  - (a) `ingest` caps children at their size-scaled store, so food beyond it is refused, the same way an adult's full reserve refuses food; or
  - (b) the child store is not size-scaled.

  Either way, the nursing `min` then removes nothing. The choice changes child physiology, so it needs its own decision and its own legacy setting.
