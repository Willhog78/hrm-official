# HRM Stage 1 — Dependent Adversarial Review — Internal

**Round:** 2  
**Date:** 2026-09-11  
**Reviewer status:** DEPENDENT / INTERNAL — same development ecosystem; not independent verification  
**Target:** `HRM_STAGE1_COORDINATION_REVIEW_CANDIDATE_v0.2.zip`  
**Primary verdict:** **CONDITIONAL PASS — CORRECTIONS REQUIRED**

## Reviewer rule

This review treats the v0.2 candidate as hostile evidence, not as a trusted builder report. Packaged pass claims were re-executed where practical, source paths were inspected directly, and additional attacks were run outside the packaged HMT harness. No candidate source was modified during the hostile review pass.

A packaged HMT PASS does not override a directly reproduced architecture defect.

## Directly verified package/reproduction results

The candidate is materially stronger and more reviewable than v0.1.

- `MANIFEST_SHA256.txt`: **PASS** — packaged file hashes verified.
- Locked activation manifest SHA-256: **MATCH** — `2e8221abf363b57463d57732334ffa2d0568ea6d749eae00ee5f4a4673d76d35`.
- Preserved HMT Run 1: **13/14 FAIL**, same manifest hash as Run 2.
- Preserved HMT Run 2: **14/14 PASS**, same manifest hash.
- Fresh reviewer HMT run: **14/14 PASS**.
- Fresh Stage-1 pytest: **33/33 PASS**.
- Fresh clean reproduction helper: **PASS**.
- Preserved/upstream Agentus regression within reproduction helper: **63/63 PASS**.
- Fresh benchmark: 25,000-way hotspot completed with exactly one commit; 25,000 partitioned proposals all committed; 400-transaction forced-failure sweep preserved a valid ledger.
- Scope scan found no substantive later-stage world semantics in Stage-1 source.

These passes are credited. They do not erase the new defects below.

## Round-1 finding dispositions

### DAR-S1-001 — Review package incomplete

**Disposition:** **CLOSED**

The v0.2 package contains the governing HMT book, master plan, Stage-1 contract, source, tests, activation manifest, raw scored evidence, journals, historical v0.1 candidate, hashes and reviewer instructions. The basis is directly reviewable.

### DAR-S1-002 — HMT execution contract not locked

**Disposition:** **CLOSED**

The activation manifest hash matches the packaged hash record. HMT Run 1 and Run 2 both identify the same manifest hash. The failed 13/14 run is preserved. No evidence was found that the acceptance contract was weakened between scored runs.

### DAR-S1-003 — HM-S01-08 Global Bottleneck Challenge red

**Disposition:** **CLOSED AS THE ORIGINAL DEFECT**

The prior serial component-dispatch loop is no longer present. Fresh HMT reproduction observed eight simultaneously active domains and passed the locked timing criterion.

The reviewer also moved the synthetic delay *inside actual authority prepare/materialize calls* rather than only wrapping `_execute_transaction`. Eight independent domains still overlapped concurrently in both phases, with approximately 0.0225 s elapsed for eight 20 ms delays. This directly supports the claim that resource-disjoint transaction work is not forced through the old serial dispatch path.

A brief global publication-registry lock still exists, but the reviewed implementation does not hold it across the transaction's resource work. This is retained as a scaling watch item, not the old Round-1 blocker.

---

# New Round-2 findings

## DAR-S1-004 — Transaction IDs are not globally unique; causal provenance can become ambiguous

**Severity:** BLOCKING  
**Disposition:** OPEN

### Attack

1. Commit epoch 0 with transaction ID `DUP-TX`.
2. Commit epoch 1 with a different proposal but the same transaction ID `DUP-TX`.
3. At epoch 2, submit a new transaction whose authoritative causal parent is `DUP-TX`.

### Observed result

Both historical transactions with `DUP-TX` committed. The epoch-2 parent reference was accepted. The ledger contained two distinct records carrying the same transaction ID, while `ledger.verify_chain()` still returned `True` and replay remained internally consistent.

### Why this is a defect

The provenance model explicitly allows a causal parent to be identified by prior transaction ID. Once a transaction ID can identify more than one prior record, the causal edge is no longer unambiguous. The ledger already maintains `_transaction_ids`, which strongly indicates run-level identity was intended, but current admission only rejects duplicate transaction IDs within a single `resolve()` batch.

The packaged HM-S01-10 test therefore overstates duplicate-ID coverage: it tests two duplicate transaction IDs in the *same batch*, not reuse across historical epochs.

### Required correction

The architecture must establish and enforce the intended identity scope before causal-state mutation. If transaction IDs are causal identifiers, they must resolve unambiguously over the declared run/replay domain. Add a hostile cross-epoch reuse test and rerun affected HMT/provenance/replay evidence.

---

## DAR-S1-005 — Logical-epoch authority is caller-trusted; stale/future attack is incomplete and stale reuse can mutate state before rejection

**Severity:** BLOCKING  
**Disposition:** OPEN

### Attack A — reuse an already-recorded epoch

1. Resolve epoch 0 normally, changing `A:x` from value/version `0/0` to `1/1`.
2. Call `resolve(0, ...)` again with a proposal also declaring logical epoch 0 and correctly expecting version 1.

### Observed result

The second transaction materialized `A:x` to `2/2`. Only afterward did `ledger.append_batch()` reject the repeated epoch with:

`ProvenanceError: epoch evidence must append monotonically and once per epoch`

The caller received an exception, but causal state remained changed to `2/2`, while the ledger still contained only the first epoch-0 transaction.

### Attack B — jump directly to a future epoch

On a clean system, `resolve(5, proposal(logical_epoch=5, ...))` was accepted and committed as the first ledger epoch.

### Why this is a defect

HM-S01-10 claims stale and future epoch rejection, but its current harness only checks whether `proposal.logical_epoch` equals the `epoch` argument supplied to the same call. The caller controls both values. It does not establish that the epoch is admissible relative to previously committed ledger/orchestrator state.

This is a false-positive coverage gap in the clock-skew card and, in the stale-reuse case, produces state/ledger divergence.

### Required correction

Define the authoritative epoch-admission rule at the coordination boundary and enforce it *before* any participant can prepare/materialize state. Expand HM-S01-10 to attack stale/repeated and skipped/future epochs relative to persisted prior evidence, not merely mismatched function arguments.

---

## DAR-S1-006 — Ledger append is not atomic with committed causal state

**Severity:** BLOCKING  
**Disposition:** OPEN

### Attack

The reviewer replaced `ledger.append_batch()` with an injected `ProvenanceError` while running a valid two-authority transaction.

### Observed result

- `A:x` materialized to value/version `1/1`.
- `B:y` materialized to value/version `1/1`.
- `resolve()` raised the injected ledger exception.
- Ledger record count remained **0**.
- Ledger epoch-block count remained **0**.
- `ledger.verify_chain()` returned `True` because the empty ledger is internally valid.

### Why this is a defect

The active Stage-1 contract requires every committed state change needed for replay to be reconstructable/auditable from ledger evidence. The architecture document also says all potentially fallible transaction work remains pre-publish, yet ledger append occurs after materialization and is demonstrably fallible.

This is broader than the repeated-epoch case in DAR-S1-005. Any post-materialization ledger-admission failure can leave committed causal state with no corresponding replay evidence.

### Required correction

The state/ledger commit boundary must be made architecturally coherent. At minimum, every rejection condition that can arise during ledger admission must be validated before publication/materialization; if ledger persistence itself can fail, the contract must provide a failure-safe publication/recovery mechanism rather than leaving state committed without evidence. Add a deliberate ledger-admission failure/mutation test and rerun atomicity, ledger completeness, replay and crash/recovery evidence.

---

## DAR-S1-007 — HM-S01-08 evidence mapping should be made explicit

**Severity:** NON-BLOCKING WATCH / CONFORMANCE CLARIFICATION  
**Disposition:** OPEN WATCH ITEM

The HMT card names parallel efficiency, lock-wait fraction and queue concentration as primary evidence. The activation manifest scores maximum simultaneous active domains, elapsed time and serial-floor speedup, while queue pressure is handled descriptively elsewhere and lock-wait fraction is not explicitly reported.

The direct reviewer attack inside prepare/materialize supports the architectural conclusion that the old global dispatch bottleneck is gone, so this is not being used to re-open DAR-S1-003. However, before the next scored package, document how the activated metrics map to the HMT card's named primary evidence, or add explicit lock-wait/queue diagnostics if that is the intended conformance interpretation.

---

# Mandatory-attack disposition

| Attack area | Round-2 reviewer disposition |
|---|---|
| Manifest precommitment | PASS — same locked hash across preserved failed/passing scored runs. |
| HM-S01-08 bottleneck | PASS for original defect — dispatch and in-transaction independent work overlap reproduced. |
| Atomic visibility | PASS for legal projection visibility under declared prepare/stage/materialize path; resource-scoped locking is real. |
| Rollback matrix | PASS for declared prepare/stage injection positions; **ledger-admission failure exposes a separate blocker (DAR-S1-006)**. |
| Replay / tamper | PASS on normal qualified path; replay provenance identity is undermined by cross-epoch duplicate transaction IDs. |
| Causality / time | **FAIL — DAR-S1-004 and DAR-S1-005.** |
| Crash recovery | PASS within the explicitly limited checkpoint/replay contract; no external WAL/database durability claim credited. |
| Seed isolation / fairness | PASS — fresh HMT rerun reproduced. |
| Mutation adequacy | PASS for the declared first-enumerated-wins mutant. |
| Authority boundary / provenance quarantine | PASS for declared legal interfaces; no later-stage truth leakage found. |
| Scaling | PASS as in-process Stage-1 evidence; no distributed scalability claim credited. |
| Scope contamination | PASS. |
| Historical integrity | PASS — v0.1 and failed Run 1 are preserved. |

# Card-level review consequence

The packaged HMT Gate still executes **14/14 PASS**, but Round 2 cannot accept that as a final Stage-1 pass because HM-S01-10 does not exercise the historical epoch/ID attacks that reproduced real defects, and HM-S01-05/HM-S01-06 do not exercise ledger-admission failure after materialization.

Cards most directly requiring requalification after correction:

- **HM-S01-05 Atomic Rollback / atomic commit boundary**
- **HM-S01-06 Ledger Completeness**
- **HM-S01-10 Clock Skew Attack**
- **HM-S01-11 Crash-and-Replay**, if the correction changes persistence/publication semantics
- **HM-S01-01 Deterministic Replay**, as regression evidence after any commit-boundary change

Other Stage-1 cards should be rerun as a complete locked regression battery once the corrected candidate exists.

# Round-2 verdict

**CONDITIONAL PASS — CORRECTIONS REQUIRED**

The underlying Stage-1 architecture is substantially improved and most hostile claims reproduced successfully. The Round-1 package, manifest and global-dispatch defects are genuinely corrected.

However, Stage 1 is **not freezeable** in v0.2 because the reviewer directly reproduced three related but substantive coordination defects:

1. causal transaction identifiers can become historically ambiguous;
2. logical-epoch admissibility is not enforced against prior committed evidence before mutation;
3. causal state can materialize successfully and then lose its ledger evidence if ledger admission fails.

These are foundational coordination/provenance defects, not cosmetic test gaps.

## Freeze decision

**DO NOT FREEZE. DO NOT CLOSE. DO NOT ADVANCE TO STAGE 2.**

Stage 1 remains **ACTIVE**.

## Builder handback

The hostile findings are now frozen. Builder work may resume with the following minimum obligations:

1. fix DAR-S1-004 through DAR-S1-006 without weakening existing HMT criteria;
2. add adversarial regression cases that reproduce each Round-2 defect before the fix and kill it after the fix;
3. retain this Round-2 report and the v0.2 candidate as negative/history evidence;
4. rerun the full Stage-1 test tree, locked HMT battery, replay/atomicity/crash regressions, benchmark and upstream Agentus regression;
5. update the Build Journal and Scratch Book with the defects, causes, corrections and results;
6. return a new immutable candidate for **Dependent Adversarial Review Round 3**;
7. after dependent review permits it, the Master Development Plan's required **independent architecture review** still remains mandatory before Stage-1 freeze.

No source correction was performed by the reviewer during Round 2.
