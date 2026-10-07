# Thirst baseline: implementation sanity (October 7, 2026)

Thirst is a baseline correction (G10.4), not an experimental question. These runs check only that the implementation is sane. Diagnostic: `experiments/genesis/run_thirst_sanity.py` (read-only planner instrumentation). Seeds `agentus-demography-a..d`, 730 days. Code at commit `9bcff76` plus the refined diagnostic.

| Check | Result |
|---|---|
| Thirst competes with hunger | 0 overrides of more urgent hunger. 25–60 decisions per run met thirst and hunger together: the agent moved to a visible cell with both water and a day's food. |
| Only perceived or remembered water | All 630 thirst moves were one step, to perceived water. No target lay outside perception. |
| Dehydration deaths drop for the right reason | 0 dehydration deaths, against 37 with the pre-G10.4 planner on the same seeds. Before thirst, 25 of those 37 were adults with water in view and 11 were dependent children whose caregivers died. |
| No new pathology | Immediate back-and-forth moves rose (about 30% → 40% of moves), consistent with commuting between food and water cells. Crowding peaked at 5–8 agents per cell, against 4–9 without thirst. Births: 5–6 per seed. All ledgers valid. |

| Seed | Alive (pre-G10.4 → baseline) | Dehydration deaths | Starvation deaths |
|---|---|---|---|
| a | 2 → 12 | 10 → 0 | 2 → 2 (infants) |
| b | 1 → 12 | 11 → 0 | 0 → 2 (infants) |
| c | 3 → 12 | 6 → 0 | 4 → 2 (infants) |
| d | 2 → 13 | 10 → 0 | 0 → 0 |

## Defect found and fixed during these checks

The first sanity pass left 2 adult dehydration deaths with water in view. Both adults were at the energy floor, so the hunger-priority rule held them on a dry food cell. The adjacent cell offered both water and a full day's food. A visible cell offering both now takes precedence (regression test in `tests/genesis/test_g10_4_thirst.py`).

## Not changed, noted for the owner

- Infants under one year still starve occasionally. That concerns caregiver provisioning, not thirst.
- Some adults sit near zero energy for weeks: a full gut of plant tissue only just covers basal cost. That is a physiology calibration question.
