# Agentus survival diagnosis — October 7, 2026

The confirmed bugs are corrected, but sustainable survival is not demonstrated. The corrected four-seed experiment performed worse on two-year survival than the baseline. This branch is a diagnostic correction, not a successful survival gate.

## Changes

- Hungry agents prioritize visible food sufficient for daily basal needs over surplus water and learned location rewards. Existing bounded exploration remains available when no adequate food is visible.
- Reproduction uses living adults at their post-movement positions. The mother must independently meet the maturity requirement. Dead or departed partners cannot qualify; newly arrived partners can.
- Existing orphan caregiver handoff accepts nearby adults across population labels. It still requires a locally reachable adult; nobody is spawned or replenished.
- Optional `--diagnose` records daily deaths, caregiver availability, food distances, and adult contact without supplying those measurements to agents.

No resource quantities, physiology calibration, environment variables, build configuration, or Railway service settings were changed.

## Same four seeds, 730 days each

Both runs were executed locally. The baseline exactly reproduces the Railway four-seed demographic outcomes. All eight final ledgers verified.

| Seed | Baseline survivors | Corrected survivors | Baseline births | Corrected births | Last corrected death day |
|---|---:|---:|---:|---:|---:|
| A | 0 | 0 | 3 | 2 | 447 |
| B | 1 | 0 | 2 | 4 | 436 |
| C | 1 | 0 | 3 | 4 | 431 |
| D | 1 | 0 | 1 | 3 | 425 |

Baseline: one extinction and three lone male survivors. Corrected: four extinctions. Births increased from nine to thirteen; no reproductively viable population remained in either experiment.

## What the trace establishes

- Baseline: death causes {'energy': 29, 'dehydration': 9}; 9 child deaths occurred after loss of the recorded caregiver.
- Corrected: death causes {'energy': 32, 'dehydration': 12, 'injury': 1}; 12 child deaths occurred after loss of the recorded caregiver.

In the baseline, some adults die with viable edible food one step away; the isolated planner regression confirms that surplus water or historical reward can override food selection. Other deaths occur where adequate food is several steps away or absent. Correcting food selection does not establish that the ecology supplies accessible food through seasonal shortages.

Adult contact also remains limited. Changing birth eligibility raises births in three seeds but does not solve adult survival or continued childcare. At least one corrected child dies from injury; this trace alone does not distinguish exposure from other injury sources.

The food measurements are post-tick measurements around the deceased agent’s previous position, not an exact replay of every intra-tick food decision. Global distances are observer diagnostics only.

## Validation

- Eight focused cognition/reproduction/caregiver tests pass. Six newly added defect cases fail on the unmodified baseline and pass with their respective corrections.
- G6 cognition gate: PASS.
- G10.2 calibration gate: PASS, including element/water accounting and checkpoint replay.
- G10.2A survival-affordance gate: PASS.
- Agentus development gate: PASS, including conserved child provisioning and hydration accounting.
- Broader suite: 101 passed, three failed before the final caregiver test was added. All three failures were reproduced independently on the unmodified baseline: consumer starvation fixture, observer snapshot fixture, and woody growth fixture. The final caregiver test and development gate passed separately.

## Next experiment

Keep resource quantities fixed. Measure actual daily intake, reserve saturation/wasted edible consumption, seasonal edible production, movement costs, and food access before changing additional behavior. Separate survival of existing adults from births and orphan mortality. Sustainable-survival qualification remains blocked.

The branch is committed locally. GitHub publication was blocked by automatic approval review pending explicit user approval.
