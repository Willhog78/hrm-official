# Caregiver energy budget and imitation audit — October 8, 2026

**Scope.** Diagnostics only. Physiology, life-history values and every model rule are unchanged.

**Tool.** `qualification/genesis/budget_audit.py`, read-only. All 8 corrected-default runs give ledger digests identical to unobserved runs (`--check-digest`). Tests are in `tests/genesis/test_budget_audit.py`.

**Runs.** 4 seeds (`agentus-demography-a..d`) × 730 days, under the D2 elapsed-time default:
- `v1@reference-v2`;
- `v1`;
- `v1` on the pre-D2 timebase, to audit the 18 imitation tries reported earlier.

**Data.** `budget_audit_*_2026-10-08.json` in this directory.

## Question 1. Where does the caregiver's energy deficit arise?

**Answer (reference-v2).** The deficit arises when a mother is nursing **two dependents at once**. On those days, milk costs more than a full gut can supply above basal metabolism:
- the gut is full on every one of those days;
- the mother is standing on more food than she can eat;
- food access, movement, temperature and interaction effort contribute almost nothing.

### How the ledger was built

Every adult's daily energy change is split into the terms that cause it, each measured where it happens:
- food credited;
- interaction effort;
- milk drawn by `_provision_dependent`;
- temperature cost;
- lean-tissue catabolism;
- basal and movement cost;
- energy given at birth.

Those terms sum to the actual change to within 5e-11 kcal on every agent-day. So the budget closes, and the terms below are measured, not inferred.

### reference-v2 (mean kcal per agent-day)

| | non-caregivers | all caregivers | caregivers, reserve < 0.75 | caregivers, reserve < 0.25 |
|---|---|---|---|---|
| agent-days | 16,495 | 6,513 | 108 | 34 |
| days with 2 dependents | — | 11% | **68%** | **100%** |
| food credited | +2,111 | +2,738 | +2,838 | +2,840 |
| milk | 0 | −762 | **−949** | −852 |
| basal | −2,000 | −2,000 | −2,000 | −2,000 |
| movement + temperature + interactions | −10 | −4 | −27 | −11 |
| net change | +98 | −30 | **−139** | −24 |
| gut full | 96% | 97% | **100%** | **100%** |
| own cell holds ≥ one full gut | 96% | 96% | **100%** | **100%** |
| lean tissue catabolized | 0 | 0 | 0 | 0 |

### How the deficit arises, step by step

All from the code and these measurements.

1. **The gut is the intake ceiling.** `bite_cap_kg` is 1.35 kg/day. A mixed diet of plant tissue (1,760 kcal/kg credited) and seed (2,850 kcal/kg) gives about 2,840 kcal on the hungry days, and the gut is full on all of them.
2. **Milk costs the mother 1.25 kcal per kcal delivered** (`lactation_efficiency` 0.8). At full dependence that is up to 687.5 kcal per child per day; the measured average is 684.5 per dependent across all caregiver days.
3. **Children overlap.**
   - The birth interval is one year (`reproduction_cooldown_ticks` 365).
   - Dependence is full to age 2 and tapers to zero at age 5.
   - So a mother can carry a second dependent while the first still nurses.
   - With one dependent, 2,000 + about 690 is within reach of a full gut. With two (up to 1,375 kcal of milk) it is not.
4. **The taper stops the fall.** Below 10% of the 120,000 kcal store (12,000 kcal), milk tapers with the mother's reserve: 566 kcal per dependent at reserve < 0.75, and 426 at reserve < 0.25. The net loss therefore shrinks from −139 to −24 kcal/day, and no mother catabolizes lean tissue. The cost of the shortfall moves to the children, who receive less milk. No child died of energy in these runs.

**An accounting rule that shapes the label, not the energy.** The planner's "hungry" threshold uses the 30,000 kcal satiety reference (reserve < 0.75 means below 22,500 kcal), while the v2 store holds 120,000 kcal. A v2 mother is labelled hungry once she has spent four fifths of a full store, long before any physical limit. That is why v2 hunger is rare and then deep.

### reference-v1 for contrast

| | caregivers | caregivers, reserve < 0.75 | caregivers losing energy |
|---|---|---|---|
| agent-days | 6,285 | 82 | 199 |
| days with 2 dependents | 4% | 0% | 7% |
| milk | −363 | −350 | −373 |
| food credited | +2,372 | +2,585 | +2,298 |
| net change | **+4** | **+202** | −98 |
| gut full | 99% | 100% | 82% |

- Under v1, milk costs 350 kcal at no efficiency loss, so caregivers break even.
- Their hungry days are recovery days: +202 kcal/day with a full gut. That is the store refilling from a low point, not a deficit.
- The days they do lose energy are mostly days the gut was **not** filled. On 18% of those days the own cell held less than a full gut of food. In v1 the occasional caregiver loss is a food-access event; in v2 the deficit is structural.

### What this does and does not establish (for D3)

**Established by measurement:**
- under v2, the caregiver deficit is milk for two overlapping dependents, on a full gut;
- under v1 there is no structural deficit.

**Not established:**
- whether a 1-year birth interval with 5-year dependence is biologically reasonable for this organism;
- whether v2's 550 kcal/day per child at 0.8 efficiency is the right milk demand.

Both are physiology and life-history inputs. They are unchanged here, and choosing between them is D3.

### Reconciliation: 400 versus 34 caregiver-days below reserve 0.25

`ECOLOGY_OPPORTUNITY_OPENING.md` section 5.1 reported 400 caregiver-days below reserve 0.25 under `reference-v2`, and this audit reports 34.

**The difference is the configuration, specifically the consumer timebase. It is not the population or the measurement definition.** Both counts are adults caring for a dependent, with reserve = energy ÷ 30,000 at the start of the day. Each method was run on both timebases (4 seeds × 730 days, `reference-v2`):

| Caregiver-days below reserve 0.25 | pre-D2 (`per-tick-legacy`) | D2 (`elapsed-time-v1`) |
|---|---|---|
| opportunity census | **400** | **34** |
| budget audit | **400** | **34** |
| hungry caregiver-days (reserve < 0.75), census and audit | 544 | 108 |

The 400 came from the census run before the D2 correction; the 34 from the audit after it.

The likely pathway runs through the predator:
- **Pre-D2**, the predator starved early: 0–6 attacks per seed in two years and no injury deaths. There were 923 caregiver-days with two dependents, and all 400 deep days had two.
- **Under D2**, the predator survives: 8 injury deaths, 7 of them children. Two-dependent days fall to 736, and deep days to 34.

Two-dependent days fall 20% while deep days fall 92%. This fits the loss of a second child ending a mother's drawdown before her store runs low. That per-mother pathway is **inferred**; it was not traced mother by mother. The attribution of 400 versus 34 to the timebase is **measured**.

The mechanism found here holds on both timebases: on every deep day the mother has two dependents, a full gut and food in her cell. The timebase changes how often a mother gets there, not why.

## Question 2. What prevented each copied act from paying off?

**Answer.** All 72 imitated tries were scored on their cost, because nothing they did was followed by food, and in this world nothing ever pays them back later. Across the three runs:

| | pre-D2 v1 | v1 | reference-v2 |
|---|---|---|---|
| tries / agents | 18 / 8 | 11 / 6 | 43 / 8 |
| same act tried twice in one day | 4 | 2 | 3 |
| imitator hungry at the time | 1 | 1 | 1 |
| what had been seen | matter appeared or changed form: 22 of 22 events | 13 of 13 | 45 of 46, plus 1 "changed form + food exposed" |
| same-day reward equals effort cost only | 18 | 11 | 42 (+1, below) |
| injured, captured or ate as a result | 0 | 0 | 0 |
| value positive by end of run | 1 | 0 | 0 |

### What was copied

All but one were **preparation acts**: separating bark, strands, wood or tendon, breaking or pushing woody stems, twisting or interlacing strands, and arranging loose wood. The imitator saw a conspicuous change in matter (salience 1–2), and in no witnessed event was the actor seen eating because of the act. So imitation copied what was visible, not what had been useful.

### Why each failed, case by case

The full per-try records are in the JSON: who was copied, when, the conditions, the effort, what was produced and eaten, and the value before, after the day and at the end.

1. **71 preparation tries.** The same-day reward is `(gain − effort)/basal − 2·injury`, and `gain` counts only food eaten from a capture or a cut. A preparation act therefore scores exactly −effort/basal (3–30 kcal, i.e. −0.0015 to −0.015), by construction. It can pay only later, by credit flowing back through the object's history when the object helps produce warmth or food. In this world neither route delivers. Over 2 years, all 4 seeds and both physiologies (`experiments/genesis/run_delayed_credit_routes.py`):
   - **Warmth saved by worn material: 0 kcal in all 8 runs.** No worn object and no interlaced surface existed at the end of any run. Temperature stress is small anyway: 0.5–4 kcal per adult-day in the ledger.
   - **Food from capture or cutting: 0–0.06 kg of fresh tissue per seed in two years**, from 0–3 captures. Sated agents fill their gut with seed and plant tissue first.

   So there was nothing to credit back. The one later-positive case (pre-D2, `separate:arranged_wood`, ending at +0.002 and reused once) did receive later credit. Its route was not traced.
2. **The one cut** (`reference-v2`, seed b, day 438, `cut:fresh_tissue|stone_heavy`):
   - The cut exposed 0.16 kg of fresh tissue.
   - The imitator was at 118,000 of 120,000 kcal and filled its gut with 0.45 kg of seed and 0.9 kg of plant tissue, and ate none of the tissue.
   - Gain was therefore zero, and the reward was the effort cost.
   - The agent it copied had also exposed tissue and eaten none of it.

### What this does and does not establish

**Established:**
- in this world, the acts available to copy are acts whose benefit, if any, arrives only through warmth or meat;
- agents here are neither cold nor short of food, so those benefits never arrive;
- imitation also copies by visible change, not by visible benefit.

**Not established:** that imitation generally fails to pay. 72 tries in one food-rich, mild world say nothing about a world where warmth or meat matters. This is the same finding as the opportunity census, seen from the act side.

## Injury deaths: now attributed by cause tracking

The audit records each day's injury gain by source:
- predator (unprovoked attack);
- ingestion hazard;
- interactions (capture, defensive bites, tools);
- physiology (exposure and fire, net of healing).

An injury death is attributed by its injury sources over the agent's last 60 days.

| Run | Injury deaths | Attributed to unprovoked predator attack | Who |
|---|---|---|---|
| v1 | 7 | 7 (98–100%) | 5 children (about 4 bites each), 2 adults (21–22 bites in 60 days) |
| reference-v2 | 8 | 8 (97–100%) | 7 children, 1 adult |
| v1, pre-D2 timebase | 2 | 2 (100%) | 2 children |

Other recorded totals:
- No death was attributed to defensive bites, ingestion or exposure.
- Predator attacks on Agentus, summed over 4 seeds:
  - `v1`: 110 in year 1, 101 in year 2;
  - `reference-v2`: 67, then 158.

These counts depend on the encounter rate, which is about 14× higher per year at daily than at monthly ticks (D2 note, section 8). They are not ecologically calibrated.

## Open decisions this informs

- **D1** (ecology opening, section 7): every injury death traced so far comes from the unprovoked, foodless bite.
- **D3:** v2's caregiver deficit is real accounting under its own inputs. The choice is about those inputs, not about food.
- **Encounter frequency** at daily ticks needs a decision of its own before predator-related mortality is interpreted.
