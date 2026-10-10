# Frontier trials are excluded before the probability draw

Three unchanged, untrained 365-day PR #50 worlds were observed. All config fingerprints and ledger hashes match their captured counterparts exactly. Chains, element/water/lithic conservation and observer consistency checks pass. No runtime code, agent knowledge, action rule, reward or production setting changed.

## Actual live choice calls

| Seed | Chooser calls | Calls reaching guarded frontier stage | Calls with eligible candidates | Trial draw declined | Actual frontier selection |
| --- | ---: | ---: | ---: | ---: | ---: |
| demography-a | 3,243 | 2,969 | 7 | 6 | 1 |
| demography-b | 3,236 | 2,990 | 4 | 4 | 0 |
| g10-4-01 | 3,272 | 2,993 | 0 | 0 | 0 |
| Total | 9,751 | 8,952 | 11 | 10 | 1 |

Only **0.123%** of guarded frontier-stage calls had an eligible candidate. Earlier choices included 776 ordinary novelty selections and six imitation selections. The one frontier selection was releasing a bark strand, as already reported by PR #50. A higher trial probability would affect only the few eligible calls in these unchanged trajectories; an intervention could subsequently change trajectories, which this observation does not predict.

## Offered option entries, with ordered exclusions

| Classification | Entries |
| --- | ---: |
| Untried single action, outside known-action frontier | 22,254 |
| Reserve blocked | 190 |
| Preempted by ordinary novelty | 7,119 |
| Preempted by imitation | 60 |
| No retained same-action attempt | 54,830 |
| Retained attempts, no matching physical before-state | 52,271 |
| Matching attempt, no enabled successor | 23 |
| Attempt budget exhausted | 0 |
| Eligible, actual frontier draw declined | 17 |
| Eligible, selected key | 2 |
| Total offered option entries | 136,766 |

These option-entry counts form a partition. They are not agent-days or independent trials. Several entries can occur on one call, including duplicate entries with the same key. The two selected-key entries correspond to **one** actual physical choice. Of 107,143 known, reserve-ready, unpreempted option entries, 107,101 lacked a retained attempt or physical match. No sampled entry reached the attempt cap.

`no_retained_attempt` does not prove forgetting caused the failure. It says only that the known action lacked an own retained transition at that choice; never having such a record, age expiry and bounded eviction are not separated here. Single-action values and retained physical transitions have different lifecycles.

## Wood and surfaces remain in scope

| Key | Untried | Prior-choice preemption | No retained attempt | Physical mismatch | Eligible frontier entry |
| --- | ---: | ---: | ---: | ---: | ---: |
| Force wood | 936 | 348 | 3,058 | 2,889 | 0 |
| Arrange loose wood | 437 | 20 | 416 | 516 | 0 |
| Extend held surface | 46 | 0 | 0 | 0 | 0 |
| Grasp surface | 253 | 38 | 705 | 962 | 3 |
| Wear surface | 282 | 13 | 137 | 100 | 0 |

All 46 extension entries were still untried at the time of offering; the single actual attempt did not encounter a later offered known-extension retry in these worlds. Raising the known-action frontier probability cannot directly address those entries. The three grasp-surface frontier entries all had declined draws. Force/arrange had no eligible frontier candidate at all.

## Physical mismatch is usually broad

The closest retained same-action before-state differed in weather for **51,718 of 52,271** mismatching entries (98.94%). Other overlapping differences were held material 48,031; available acts 47,602; pools 45,014; ground objects 41,432; local position 29,122; geometry 8,908; worn material 2,484; injury 2,357.

For force wood, weather differed on 2,863/2,889 closest mismatches and pools on 2,861. For arranging, weather differed on 513/516, pools on 496, geometry on 486 and held material on 483. Those overlaps matter: dropping weather alone is not shown to rescue these states. The closest record is selected by fewest differing top-level fields, not causal relevance. One field may contain multiple quantities. These observations do not establish that any mismatch can safely be ignored.

## Next implementation boundary

The immediate barrier is retrieval/recognition of enabling experience, rather than the eight/16 attempt cap or trial probability. Whole-scene state matching and the differing lifecycles of action values versus retained transitions warrant targeted work. Simply increasing exploration, extending a global trace, or discarding all weather/material features is not supported by this audit.

The next coordinated change should test bounded action-specific prerequisite recognition: retain the actor's actually experienced preparation, identify the local material/access cues relevant to that interaction, and reject unmet live constraints before each step. Controlled validation must include both irrelevant environmental drift and genuinely altered material, wetness, reach and injury. It must not introduce an observer-labelled goal, a construction recipe, a transferred reward or direct application of a remembered outcome. Useful physiological benefit and repeated ecological practice still have to be earned; cultural transmission remains unproven.

## Verification

All **30 selected checks passed in 33.87 seconds**, including 12 new observer checks, 14 frontier-recognition micro checks, two version/replay checks and two existing discovery-observer checks. The new complete 20-day observed/unobserved snapshots and ledgers are identical. Exception handling restores the context's original draw and global chooser. All three year-long comparisons match prior hashes, with zero diagnostic consistency errors. `git diff --check` passes. No full repository suite was run for this read-only addition.

Raw evidence: `FRONTIER_EXCLUSIONS_2026-10-10.json`. Definitions and reproduction: `docs/architecture/FRONTIER_EXCLUSION_DIAGNOSIS.md`.
