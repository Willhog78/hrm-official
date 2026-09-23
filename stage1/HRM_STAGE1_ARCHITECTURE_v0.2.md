# HRM Stage 1 — Coordination Architecture v0.2

## Status

Corrected post-HMT implementation. The locked Hugh Mann Test v0.2 Stage-1 Gate battery passes 14/14 in scored Run 2. Stage 1 remains **ACTIVE — NOT FROZEN / NOT CLOSED** pending adversarial review and the remaining governance sequence.

## 1. Temporal Orchestrator

`TemporalOrchestrator` owns logical contract epochs and schedule metadata only. Each scheduled producer has an explicit integer cadence, phase and feedback-lag declaration. In Stage 1 the feedback lag must be exactly 1 tick: that is the only lag the ledger enforces (causal parents must be prior-epoch evidence), so larger declared lags are rejected at registration rather than accepted unenforced. All due producers read the same pre-commit epoch state. Their proposals are collected before arbitration, so callback enumeration order cannot create same-epoch recursive read-after-write priority.

The implementation uses an exact rational `contract_dt` plus integer logical epochs. Host wall-clock timestamps do not control causality. Stale/future logical epochs are rejected by the transaction fabric.

## 2. Transaction / Arbitration Fabric

The fabric receives proposals containing expected versions and resource mutations. A resource is identified by `(authority_id, resource_id)`. The authority ID determines canonical ownership; coordination never receives a direct mutable kernel-state mapping.

### Conflict domains and real concurrent dispatch

Resource overlap is converted into connected conflict-domain components with union-find. Components that share no resource key are independent. Arbitration completes deterministically before state execution.

In v0.1 these domains were semantically explicit but still executed through one serial component loop. HMT Round-1 testing correctly marked that behavior red. In v0.2, independent domains are dispatched through a bounded `ThreadPoolExecutor` by default. A caller may still request an explicit serial component permutation for equivalence testing.

The causal result does not depend on host thread scheduling because:

1. winner selection is deterministic before dispatch;
2. concurrently dispatched domains own disjoint conflict keys;
3. result collection is normalized by proposal ID;
4. replay evidence is merged canonically at the epoch boundary.

The locked HM-S01-08 scored challenge observed 8 simultaneously active independent domains and completed the injected 0.160-second serial-floor workload in approximately 0.0236 seconds.

### Deterministic arbitration

Within a real conflict domain, proposals are ranked by a hash of run seed, epoch, proposal ID, transaction ID and conflict keys. Enumeration order is not a priority rule. Duplicate proposal IDs and duplicate transaction IDs in the same batch are rejected.

**Trust assumption (recorded post-Round-2, not a reviewed verdict):** proposal and transaction IDs are proposer-chosen and the run seed is readable by kernels, so a kernel deliberately written to game arbitration could search for IDs that win conflicts. The hash removes accidental bias from ID naming or sort order; it does not defend against deliberate gaming. Stage 1 treats kernels as non-hostile, consistent with deferring hostile-process isolation to a process/distributed boundary. Closing this gap would require ranking on non-proposer-chosen inputs or commit-reveal, and is not implemented.

### Malformed proposals

Batch-integrity errors fail the whole `resolve` call with no state or evidence change: missing proposal/transaction/proposer IDs, duplicate proposal or transaction IDs within the batch, proposal/epoch mismatch, inadmissible epoch, and historical transaction-ID reuse. Proposer-attributable defects reject only the offending proposal and are recorded as `REJECTED` ledger evidence (burning its transaction ID): empty mutation list, duplicate mutation resource, unknown authority, unknown resource key, and invalid authoritative provenance. Other proposals in the epoch proceed. `plan_conflict_domains` still raises on any shape defect.

### Stale reads

Every mutation carries an expected version. The owning authority validates that version at prepare time. A stale read rejects rather than silently committing against newer state.

### Cross-partition atomicity and observable publication

A transaction may span multiple independently owned authorities. Atomic commitment has three phases:

1. **Prepare** — each participant validates ownership/version and creates a private prepared write.
2. **Stage commit** — each participant moves the prepared write into non-visible staged state. Failures remain legal; any failure aborts all participants.
3. **Publish/materialize** — only after every participant stages successfully does the fabric record a publish decision and materialize staged changes.

v0.2 strengthens the original barrier with **resource-scoped publication locks**. The fabric acquires every resource lock touched by a transaction in canonical order and holds those locks across prepare → stage → publish → materialize. Legal projection reads acquire the same resource locks. Therefore a concurrent reader cannot observe participant A after A materializes while participant B is still pending.

The locks are per resource, not global. Independent conflict domains therefore remain concurrently executable. HM-S01-05 deliberately pauses a successful three-authority transaction between participant materializations and confirms a legal read of the already-materialized resource remains blocked until the entire transaction is visible.

All potentially fallible transaction work remains pre-publish. Post-publish materialization is still an adapter contract: a later real kernel must provide staging/recovery semantics sufficient to make its final promotion non-failing. If it cannot, that is a Stage-1 adapter/architecture defect requiring review rather than a hidden compensating shortcut.

## 3. Provenance / Replay Ledger

Replay evidence remains epoch-segmented rather than a single per-event global hash chain.

Each valid proposal receives an independently hashable evidence record anchored to the previous epoch root. At the synchronization boundary, sorted record digests are merged into one deterministic epoch evidence root. Empty epochs also produce a deterministic evidence block so “time advanced with no accepted change” is distinguishable from “the epoch never occurred.”

The ledger records proposal and arbitration digests, committed version/value transitions, causal parents, source authority, operation label, run/config fingerprint, fallible claims and prior epoch root. Replay reconstructs synthetic canonical state from genesis and verifies version continuity.

Authoritative causal parents must be **committed** records from prior-epoch evidence. Same-epoch causal-parent claims are rejected under the explicit feedback-lag contract, and so are citations of REJECTED records, which record a refusal rather than an event. `verify_chain` enforces the same rule on imported evidence. Record IDs encode the (transaction ID, proposal ID) pair as canonical JSON, so IDs containing separators cannot collide.

### Authoritative versus fallible information

Authoritative causal provenance is audit infrastructure only. `fallible_projection()` exposes explicitly marked claims while omitting authoritative source/parent/digest/config fields. Coordination knowledge therefore does not become automatic agent knowledge.

## 4. Seed isolation

Stage 1 now includes `SeedBank`, a deterministic namespace-based seed derivation utility. A component-local random stream depends only on the master seed and explicit stream ID. Consuming an unrelated stream cannot advance or perturb another stream.

This is coordination infrastructure, not a behavioral randomness model. HM-S01-12 verifies both stream isolation and target-domain arbitration stability when unrelated seeded activity is added.

## 5. Authority boundary

`StateAuthority` remains a synthetic qualification fixture rather than a Stage-2 kernel. Canonical state and versions are private. Coordination receives only a closure-backed `AuthorityPort` supporting snapshot, prepare, stage, abort, materialize and checkpoint operations.

Synthetic failure/delay hooks exist only on the fixture to exercise hostile transaction cases. They are not world mechanisms.

## 6. Checkpoint / crash recovery

Checkpoints are legal only at clean transaction boundaries. They persist logical epoch/schedule metadata, authority values and versions, run seed, maximum domain-dispatch setting, and replay evidence.

HM-S01-11 kills fresh subprocesses at eight declared points: after prepare(A/B), stage(A/B), materialize(A/B), ledger append and immediately before the next clean checkpoint. Recovery from the last clean checkpoint in a fresh process exactly matches the uninterrupted terminal state/replay root with no duplicate transaction IDs.

This qualifies the declared Stage-1 checkpoint persistence contract; it is not a claim that an external database or distributed WAL has already been implemented.

## 7. Explicit non-claims

- This build does not empirically validate physical, biological, cognitive or social behavior.
- In-process Python thread overlap is evidence against one mandatory serial component-dispatch path; it is not proof of distributed/multicore production scalability.
- The synthetic `StateAuthority` is a qualification fixture. Stage 2 must adapt actual Matter ownership to the interface rather than moving Matter state into coordination.
- No observer or later-stage semantic label controls causal state.
