# Caregiving: nursing, mobility and solid food (design and risk, 2026-10-08)

**Owner decision.** Allow caregivers to give children solid food, through a physical transfer:
- the adult must obtain food and have access to the child;
- the adult transfers a finite amount and loses exactly what the child receives;
- the child's ingestion stays subject to the child's capacity;
- children still forage according to their abilities.

This provides a capability. It does not guarantee that caregivers use it successfully. No weaning age is chosen to remove the measured deficit, and physiology defaults are unchanged (`reference-v1`).

## 1. What is bundled today

One age curve, `caregiver_dependence`, drives three things (`biology._age_profile`): 1.0 to age 2, falling linearly to 0 at age 5.

| Role | Today |
|---|---|
| Nursing (milk energy, water, dry mass) | `_provision_dependent` scales by `caregiver_dependence`. |
| Mobility | `caregiver_dependence > 0` means the child goes to its caregiver (carried if co-located at the start of the day, else one cell a day). |
| Feeding | Below 1.0 (after age 2) the child forages for itself; below 0 (age 5) it also interacts. There is no other caregiving. |

## 2. Design

**Separate the three roles, with unchanged values.** `_age_profile` now publishes three named factors:
- `nursing_factor`;
- `carried`;
- `self_feeding`.

Each is computed from the same age curve as before, so every existing run is bit-identical. Nursing reads only `nursing_factor`, movement only `carried`, and own foraging only `self_feeding`. Changing one later, for example a different weaning curve, no longer moves the others. No value is changed here.

**Add solid-food provisioning** (`caregiving_model = "solid-food-v1"`; `"none"` reproduces earlier runs). On the child's turn (children act after their caregivers), after nursing and after the child's own foraging, the caregiver gives food when all of these hold:
1. the child is at least `SOLID_FOOD_ONSET_DAYS` = 180 days old. This is a declared biological reference: complementary feeding in humans begins around six months. It is not a weaning age; milk continues unchanged;
2. the child is still dependent (`nursing_factor > 0`) and shares the caregiver's cell;
3. the child shows hunger, by the planner's own threshold (reserve < 0.75 of its satiety reference). This is a visible cue;
4. the child's gut has room left today (its age-scaled `bite_cap_kg` minus what it already ate);
5. food the caregiver knows as food (positive learned value) is physically present in that cell.

The transfer:
- **Obtain.** The caregiver takes mass of those kinds from the cell into its hands, in order of its own learned value. It is limited by the child's remaining gut room and by the kind's adult hand access (seed 0.45 kg, fresh tissue 0.25 kg; plant tissue has no hand limit).
- **Hand over.** The child ingests from the caregiver's hands with the child's own assimilation and hazard, exactly as eating. Unassimilated mass goes to the cell's detritus. Anything not ingested is put back in the cell the same day. Nothing is stored or carried overnight.
- **Cost.** The caregiver pays the kind's handling energy for the mass it obtained, at adult scale. The child pays nothing.
- **Exactness.** The caregiver's hands gain what was taken and lose exactly what the child ingested, plus what was put back. Elements are conserved: cell → hands → child body or detritus, or back to the cell.
- **No learning in v1.** The child's food values are not updated by provisioned food. Whether eating what a caregiver hands over teaches the child a food kind is a separate social-learning question, and it is recorded as a measure only.

## 3. Risks, and what will be measured

| Risk | Why it matters | Mitigation or measure |
|---|---|---|
| Milk demand does not respond to solid food | `_provision_dependent` draws milk at `cap × nursing_factor` whatever the child eats. The measured v2 maternal deficit therefore cannot shrink through solids, and the caregiver now also pays handling. | Report caregiver net energy before and after. Measure milk delivered against the child's room to absorb it (wasted milk). Demand-limited milk would be a separate decision. |
| Child energy store is not size-scaled when eating | `ingest` caps energy at the adult `energy_capacity_kcal`. Nursing caps at capacity × development scale. Provisioned and self-foraged food can fill a child's store to adult size. This is pre-existing for children aged 2–5. | Report child reserves. Do not fix silently. Flag as a known defect for a separate change. |
| Provisioning becomes a scripted rescue | Automatic help whenever conditions hold could make child survival a design outcome. | Success depends on physical conditions: co-location, food actually in the cell, the caregiver's knowledge of food kinds, the child's gut and hunger. Report attempts, transfers, failures by cause, and child deaths. Nothing is tuned toward a survival count. |
| Infants (180 days to 2 years) eat solids for the first time | Infant survival and growth change. | The onset age is a declared reference, not tuned. Report infant intake and deaths. |
| Accounting gaps in the audit | A new energy and mass path. | The budget audit adds a provisioning term. The energy ledger must still close, and conservation checks hold. |

## 4. What this does not change

- Nursing amounts, the dependence curve, mobility, physiology defaults, birth spacing and milk cost: the values are unchanged.
- Agentus cognition and social learning.
- Animal rates and opportunities, and plant rates.
