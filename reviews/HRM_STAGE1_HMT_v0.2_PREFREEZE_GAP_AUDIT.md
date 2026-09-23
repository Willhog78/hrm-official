# HRM Stage 1 — Hugh Mann Test v0.2 Pre-Freeze Gap Audit

**Date:** 2026-09-11  
**Basis:** `The_Hugh_Mann_Test_v0.2.docx`, `HRM_MASTER_DEVELOPMENT_PLAN_v1.1.md`, and `HRM_STAGE1_COORDINATION_REVIEW_CANDIDATE_v0.1.zip`  
**Decision:** **DO NOT FREEZE STAGE 1 YET.**

## Why

HMT v0.2 defines 14 Stage-1 Coordination Architecture cards and adds an enforcement layer requiring active cards to have locked execution contracts before a scored verdict. Gate qualification is the full active-stage battery, including required mutations/negative controls and evidence packaging. The existing Stage-1 candidate predates this HMT activation layer, so its existing results are useful regression/development evidence but are not, by themselves, a complete HMT v0.2 scored Gate battery.

## Card-by-card crosswalk

| HMT card | Current status | Existing evidence | Pre-freeze action |
|---|---|---|---|
| HM-S01-01 Deterministic Replay | PARTIAL | Deterministic enumeration/order test; fresh-process checkpoint continuation | Add clean-process full rerun of identical initial state/seed/event stream and compare state + event/replay hashes exactly. |
| HM-S01-02 Causal Order Integrity | PARTIAL | Unknown/same-epoch provenance parent rejected; feedback lag exists | Add explicit chained-causality cases with adversarial scheduling/order perturbation; require zero inversions. |
| HM-S01-03 Simultaneous Conflict Arbitration | COVERED IN SUBSTANCE | Reversed proposal-order conflict test; deterministic arbiter | Activate/score under HMT manifest and retain raw arbitration traces. |
| HM-S01-04 No Double Spend | COVERED IN SUBSTANCE | Two proposals for one versioned resource cannot both commit | Add/label explicit exclusive-resource scenario in HMT harness and score it. |
| HM-S01-05 Atomic Rollback | PARTIAL | Local stage failure; required cross-partition forced stage failure; repeated 400-tx sweep | Expand fault matrix to each legal intermediate phase/participant position, not only injected stage-commit failure. |
| HM-S01-06 Ledger Completeness | COVERED IN SUBSTANCE | Replay reconstructs state; chain verification; tamper detection | Add HMT trace-completeness report over sampled/all terminal variables and score it. |
| HM-S01-07 Contention Load Test | PARTIAL | 1k/5k/10k/25k hotspot and partitioned sweeps | Lock HMT primary metric/acceptance region first; rerun controlled Gate evidence. Add latency/queue-depth or explicitly justify unavailable metric. |
| HM-S01-08 Global Bottleneck Challenge | **CURRENT RED / UNSATISFIED** | Conflict domains are explicit and permutation-invariant | Current `resolve()` executes independent components through one serial loop. Diagnostic with 8 independent domains observed max simultaneous active transactions = 1 and ~0.163 s for eight injected 20 ms operations (serial floor 0.160 s). Architecture/test must be corrected before freeze if HMT v0.2 is controlling. |
| HM-S01-09 Partition Equivalence | PARTIAL | Multi-domain component execution order invariance | Add logically identical single-partition vs multi-partition workload comparison; require semantic equivalence. |
| HM-S01-10 Clock Skew Attack | MISSING AS DIRECT CARD | Epoch mismatch checks and same-epoch arbitration exist | Explicitly inject stale, future, duplicate-ID/equal-time cases and score declared handling semantics. |
| HM-S01-11 Crash-and-Replay | PARTIAL | Fresh-process checkpoint restart after 3 clean epochs | HMT asks randomized transaction-point interruption. Add crash/fault-point recovery cases and verify no lost/duplicated committed actions versus uninterrupted reference. |
| HM-S01-12 Seed Isolation | MISSING | Arbiter uses deterministic seed hashing, but no isolation challenge | Add no-op stochastic consumer/independent stream perturbation test; unrelated outcomes must remain unchanged where isolation is promised. |
| HM-S01-13 Fairness Under Symmetry | MISSING | No ensemble fairness test | Predeclare seed list, primary balance metric, multiplicity handling and 95% CI; run symmetric contenders across many seeds/orderings. |
| HM-S01-14 Mutation: Break the Arbiter | MISSING | No deliberate arbiter mutant evidence | Create disposable mutation that disables/alters an arbitration guard and prove the Stage-1 suite kills it reliably. |

## HMT v0.2 execution-contract issue

Before the new HMT-scored runs, create a Stage-1 activation manifest that locks for each card: maturity state, HM tier, run/seed plan, primary metric, numeric acceptance region/tolerance, uncertainty target, multiplicity rule where relevant, exclusions, and execution lane. Do not retroactively invent thresholds and label already-observed results as confirmatory HMT evidence.

## Immediate architectural finding — HM-S01-08

A diagnostic was run against the current candidate without changing it:

- independent conflict domains: 8
- injected work per domain: 20 ms
- maximum simultaneously active transactions observed: 1
- elapsed: ~0.1632 s
- serial sleep floor: 0.1600 s

This confirms that semantic partitionability exists, but current execution still has a mandatory serial component-dispatch path. The existing active contract allowed process/distributed scaling proof to wait until later, but HMT v0.2's Stage-1 Global Bottleneck Challenge is stricter. If HMT v0.2 is part of the governing project evidence for Stage 1, this must be resolved or explicitly adjudicated before freeze; it should not be silently called PASS.

## Governance consequence

Stage 1 remains **ACTIVE / NOT FROZEN / NOT CLOSED**. The correct sequence is:

1. lock the HMT Stage-1 activation/execution manifest;
2. implement the missing/expanded HMT harness;
3. correct HM-S01-08 if the Stage-1 HMT card is controlling;
4. run the complete 14-card Gate battery and preserve raw evidence/negative results;
5. update the Build Journal and Scratch Book with findings/corrections;
6. submit the revised Stage-1 candidate for independent adversarial architecture review;
7. correct any substantive review defects and rerun affected evidence;
8. journal the final verdict;
9. only then freeze/close Stage 1 and advance.
