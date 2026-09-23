# HRM Stage 1 — Hugh Mann Test v0.2 Activation / Execution Manifest

**Status:** LOCKED BEFORE HMT-SCORED GATE RUNS  
**Date locked:** 2026-09-11  
**Stage status at lock:** ACTIVE — NOT FROZEN / NOT CLOSED  
**Controlling HMT:** `The_Hugh_Mann_Test_v0.2.docx`  
**Controlling stage contract:** `HRM_STAGE1_ACTIVE_CONTRACT_v1.1.md`  
**Round-1 hostile handback:** `HRM_STAGE1_DEPENDENT_ADVERSARIAL_REVIEW_ROUND1.md`

## Lock rule

This manifest fixes the Stage-1 HMT scoring rules before any new run is counted as confirmatory HMT Gate evidence. Development/regression runs performed before this lock may be retained as supporting evidence but may not be relabeled as the scored HMT Gate battery.

After the first scored run, a failing criterion may be corrected in implementation and rerun **without weakening the criterion**. Any proposed criterion change requires explicit adjudication, preserved old result, a manifest revision, and a new scored run; it may not be silently tuned to obtain a pass.

## Shared execution rules

- Python lane: CPython 3.x, package-local source via `PYTHONPATH=src`.
- Deterministic cards use exact equality unless a numeric threshold is explicitly stated below.
- HMT-1 stochastic/seeded cards use frozen seed families defined below; seed formulas are part of this lock.
- Raw JSON evidence, stdout/stderr, environment/version data, and pytest output must be retained.
- Failed and surprising scored runs remain in evidence and in the Build Journal.
- Stage 1 is architecture-only: no Matter, climate, ecology, cognition, social, institution, technology, or observer semantics may be introduced to satisfy a card.

## Frozen seed families

- HM-S01-07: `load-00` … `load-19` (20 seeds). SHA-256 of newline-joined list: `085aa2400a5d6bfeee1b0367ef1185d8c0a0525cf3453a8a9d701ef9ecf26b5e`.
- HM-S01-11: `crash-00` … `crash-07` (8 deterministic crash-case labels). SHA-256: `0173fd3e5fbb071de33f421cdea1d31d2ff96ee80b35b3dfd10c9fec64fabcfc`.
- HM-S01-13: `fairness-0000` … `fairness-0999` (1000 seeds). SHA-256: `dd8ef86880b3bcaf5208cd4bc9e61cc1a11ca193a52a6f64cc8d1a3c98aa14c1`.
- HM-S01-14: `mutant-00` … `mutant-19` (20 seeds). SHA-256: `5ac159aecb86549d8de099fe784a8e84931ffbf667af720fb21671c5ca0c27bc`.

## Activated Stage-1 cards

### HM-S01-01 — Deterministic Replay [STD/ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared cases:** one six-epoch deterministic scenario executed (a) normally, (b) repeated in-process, and (c) in a clean Python process.
- **Primary metrics:** terminal causal-state hash; complete ledger-export hash; terminal replay-root hash; per-epoch arbitration digest sequence; first divergence epoch.
- **Acceptance:** all compared hashes/digest sequences exactly equal; divergence epoch = none.
- **Uncertainty:** N/A; deterministic exact verdict.
- **Exclusions:** host wall-clock duration is not a scoring metric.

### HM-S01-02 — Causal Order Integrity [ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared case:** six-epoch causal chain with explicit prior-epoch parent references plus unrelated proposals submitted in adversarial/reversed enumeration patterns; explicit same-epoch/future-parent attack included.
- **Primary metrics:** causal inversions; illegal-parent acceptances.
- **Acceptance:** causal inversions = 0; illegal-parent acceptances = 0; every accepted causal parent resolves to evidence from a strictly earlier epoch.
- **Uncertainty:** N/A.

### HM-S01-03 — Simultaneous Conflict Arbitration [ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared case:** equal-epoch symmetric conflicting proposals under forward and reverse enumeration.
- **Primary metrics:** winner identity; arbitration digest; committed count.
- **Acceptance:** winner identity and arbitration digest exactly equal across enumeration order; committed count = 1.
- **Uncertainty:** N/A.

### HM-S01-04 — No Double Spend [ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared case:** 32 simultaneous claims on one indivisible resource/version.
- **Primary metrics:** committed claims; final ownership instances; final version increment.
- **Acceptance:** committed claims = 1; ownership instances = 1; final version = 1; duplicate ownership count = 0.
- **Uncertainty:** N/A.

### HM-S01-05 — Atomic Rollback [ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared failure matrix:** one three-authority transaction, with forced failure independently at prepare(A), prepare(B), prepare(C), stage(A), stage(B), and stage(C).
- **Additional atomic-observability case:** successful three-authority publish is paused between participant materializations while a legal projection races the transaction.
- **Primary metrics:** residual changed resources after failed transaction; participant version drift; partial observer views; rejected-ledger consistency.
- **Acceptance:** all 6/6 injected legal pre-publish failure positions leave residual changed resources = 0 and version drift = 0; no failed transaction remains published; racing observer sees either complete pre-state or complete post-state and never a mixed participant state; ledger verifies.
- **Uncertainty:** N/A.
- **Exclusion:** post-publish materialization failure is not injected because Stage-1 explicitly contracts that operation as infallible; the observer race tests visibility across that phase instead.

### HM-S01-06 — Ledger Completeness [STD/ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared case:** multi-epoch workload changing every terminal resource at least once; all non-genesis terminal variables are traced, not merely sampled.
- **Primary metrics:** trace completion rate; orphan terminal changes; replay equality.
- **Acceptance:** trace completion = 100%; orphan changes = 0; replay state exactly equals causal state; ledger verification = true.
- **Uncertainty:** N/A.

### HM-S01-07 — Contention Load Test [ENG]

- **Maturity / tier:** Gate-active; HM-1.
- **Runs:** 20 frozen seeds per condition.
- **Conditions:** proposal counts 100, 1000, 5000 × (hotspot single-resource contention, diffuse independent-resource contention).
- **Primary metrics:** invariant violations; committed/rejected accounting; elapsed seconds; throughput proposals/s; discovered conflict-domain count. Queue pressure is represented by pending independent domain count at dispatch and retained as descriptive evidence.
- **Acceptance:** invariant violations = 0 in every run; proposal accounting exact in every run; every run completes in < 30.0 s; measured throughput > 0; no silent loss/duplication. Timing/throughput distributions and 95% confidence intervals are reported but are not used to claim hardware-general scalability.
- **Multiplicity:** 6 condition families; correctness must pass every family (no alpha-spending interpretation because correctness is exact). Timing is descriptive/watchdog only.
- **Exclusions:** no claim of distributed/process scalability from this in-process lane.

### HM-S01-08 — Global Bottleneck Challenge [ENG]

- **Maturity / tier:** Gate-active; HM-0; previously RED in Round 1.
- **Declared case:** 8 independent conflict domains, each instrumented with 20 ms of released-GIL synthetic work, `max_parallel_domains=8`.
- **Primary metrics:** maximum simultaneous active domains; elapsed seconds; serial-floor speedup where serial floor = 0.160 s.
- **Acceptance:** maximum simultaneous active domains >= 4; elapsed <= 0.100 s; serial-floor speedup >= 1.60×; final state/replay correctness exact.
- **Uncertainty:** N/A. Threshold deliberately requires material overlap rather than token thread creation.
- **Non-weakening note:** the prior RED diagnostic was ~0.1632 s with max active = 1. These thresholds are fixed before the corrected scored run and may not be relaxed because of its outcome.

### HM-S01-09 — Partition Equivalence [REP/ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared case:** identical 64-domain workload executed once with one domain worker and once with eight domain workers; a reversed explicit serial component order is also compared.
- **Primary metrics:** terminal state hash; ledger root; arbitration digest; result vector.
- **Acceptance:** exact equality across all execution topologies/orders.
- **Uncertainty:** N/A.

### HM-S01-10 — Clock Skew Attack [ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared time semantics:** Stage 1 accepts only integer logical epochs as authoritative causal time; host wall-clock timestamps do not control causality.
- **Attacks:** stale epoch, future epoch, duplicate proposal ID, duplicate transaction ID, and equal-epoch conflicting proposals under reversed order.
- **Primary metrics:** rejected/normalized attack classes; causal divergence.
- **Acceptance:** stale and future epochs rejected; duplicate IDs rejected; equal-epoch conflict resolves deterministically and identically under enumeration reversal; causal divergence = 0.
- **Uncertainty:** N/A.

### HM-S01-11 — Crash-and-Replay [ENG]

- **Maturity / tier:** Gate-active; HM-0 with 8 declared deterministic crash cases selected before execution.
- **Crash points:** after prepare(A), prepare(B), stage(A), stage(B), materialize(A), materialize(B), ledger append, and immediately before the clean post-epoch checkpoint. Each case is executed in a subprocess that is intentionally terminated; recovery occurs in a fresh subprocess from the last clean checkpoint/ledger payload.
- **Primary metrics:** recovered terminal state hash; ledger root; lost events; duplicated events.
- **Acceptance:** every recovered run exactly equals the uninterrupted reference terminal state and ledger root; lost events = 0; duplicated events = 0.
- **Uncertainty:** N/A.
- **Boundary:** durability claimed here is the declared Stage-1 checkpoint/ledger persistence contract, not an external database/WAL claim.

### HM-S01-12 — Seed Isolation [ENG]

- **Maturity / tier:** Gate-active; HM-0.
- **Declared cases:** (1) `SeedBank` target stream sequence with and without heavy draws from an unrelated no-op stream; (2) target arbitration domain with and without unrelated independently seeded domain activity.
- **Primary metric:** cross-stream/target-domain divergence.
- **Acceptance:** divergence count = 0; target stream bytes/numbers exactly equal; target arbitration result/digest contribution unchanged by unrelated no-op stream activity.
- **Uncertainty:** N/A.

### HM-S01-13 — Fairness Under Symmetry [PRAC]

- **Maturity / tier:** Gate-active; HM-1.
- **Runs:** 1000 frozen seeds. Two contenders are identical except stable IDs and proposed owner labels; input order alternates and is not part of rank semantics.
- **Primary metric:** contender-A win rate; Wilson 95% confidence interval reported.
- **Acceptance:** contender-A win rate in [0.45, 0.55]; no input-order subgroup differs from 0.50 by more than 0.075; committed count exactly one per seed.
- **Multiplicity:** one primary overall balance test plus two predeclared order subgroups; all bounds must pass.
- **Interpretation:** this tests unexplained persistent scheduler/index advantage, not a claim that deterministic arbitration must make each finite seed set exactly 50/50.

### HM-S01-14 — Mutation: Break the Arbiter [ENG]

- **Maturity / tier:** Gate-active; HM-1.
- **Mutant:** disposable arbiter mutation replaces seeded deterministic rank selection with first-enumerated-wins behavior inside a conflict domain.
- **Runs:** 20 frozen seeds, each probed under forward and reverse proposal order.
- **Primary metric:** mutant kill rate by the Stage-1 order-invariance arbitration probe.
- **Acceptance:** mutant kill rate = 100% (20/20); unmutated control passes 20/20.
- **Uncertainty:** exact kill-rate verdict; no CI required for the deterministic mutant behavior, though run count satisfies HMT-1 repetition.

## Stage-level advance rule under this activation

The Stage-1 HMT Gate battery passes only if **all 14 cards pass** their locked criteria. One RED card blocks HMT qualification. A Gate pass does not by itself freeze Stage 1: adversarial review, decision, journal completion, and the project freeze/advance governance still apply.
