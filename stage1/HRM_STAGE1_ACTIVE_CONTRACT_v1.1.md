# HRM Stage 1 — Active Coordination Architecture Contract v1.1

**Status:** ACTIVE / AUTHORIZED FOR STAGE-1 IMPLEMENTATION

**Controlling plan:** HRM Master Development Plan v1.1  
**Entry baseline:** `HRM_STAGE0_CLOSED_STAGE1_CORRECTED_BASELINE_v1.5.zip`  
**Upstream reference:** Agentus Gate-9 frozen baseline `ae6034d637b3e61649efc2f895d11311af22fe730b1606270ccd4755844de434`

## Scope

Stage 1 contains only three logical responsibilities:

1. **Temporal Orchestrator** — simulation time, scheduling, multi-rate synchronization, event ordering, explicit feedback-lag policy.
2. **Transaction / Arbitration Fabric** — read → propose → validate/arbitrate → commit semantics, stale-read rejection, deterministic conflict resolution, atomicity, and routing to the authority that owns affected state.
3. **Provenance / Replay Ledger** — deterministic replay evidence, causal provenance, event history, run/config fingerprints, checkpoint/restart evidence and audit records.

These responsibilities may share a process during development but must remain separable. Coordination does not become a universal owner of kernel state.

Stage 1 is not authorized to expand Matter, climate/weather, ecology, human biology, cognition, social systems, institutions, technology, or observer classification.

## Predeclared exit criteria

| ID | Required result |
|---|---|
| S1.1 | Same initial state, seed, schedule and proposals produce identical committed causal state and replay digest. |
| S1.2 | Independently scheduled synthetic authorities run at different declared rates without hidden tick-order priority. |
| S1.3 | A proposal based on an invalidated version cannot silently commit. |
| S1.4 | Equivalent conflict sets resolve identically regardless of proposal enumeration or validation-worker order. |
| S1.5 | A failed multi-part transaction leaves no partial committed state. **This explicitly includes one transaction spanning two or more independently partitioned authorities: a forced failure on one participant during the commit path must leave no partial result observably committed on any other participant.** |
| S1.6 | Coordination may route/arbitrate but cannot mutate a kernel's private state except through its declared commit interface. |
| S1.7 | Every committed state change required for declared replay can be reconstructed/audited from ledger evidence and fingerprints. |
| S1.8 | Cross-system delays are explicit configuration/state, not accidental call-order artifacts. |
| S1.9 | Independent non-conflicting work can be partitioned/sharded without one universal conflict lock/queue; partition execution order must not change causal results. |
| S1.10 | Predeclared scaling sweeps include pathological contention and ordinary partitioned load; superlinear failure may not be hidden. |
| S1.11 | Synthetic kernels with intentionally tempting private fields remain inaccessible through legal coordination interfaces. |
| S1.12 | Relevant preserved Agentus transaction/provenance/replay tests remain reproducible or receive an explicit semantic replacement/equivalence test. |
| S1.13 | Authoritative causal provenance remains separate from agent-facing/fallible claims. No legal fallible projection exposes authoritative causal truth as belief. |
| S1.14 | Persisted checkpoint plus required ledger/config state can restart in a fresh process and produce the same subsequent committed state and replay digest as uninterrupted execution. |

## Required hostile/adversarial cases before freeze

- reversed proposal order;
- reversed worker/component execution order;
- stale read racing a valid proposal;
- two or more independent conflict domains in the same interval;
- partial failure during prepare/commit;
- **cross-partition transaction with a forced mid-commit-path failure and proof of zero partial observable commit;**
- malformed authoritative provenance;
- replay under equivalent seed/schedule;
- persisted checkpoint → fresh-process restart → deterministic continuation;
- attempt to obtain authoritative causal provenance through a fallible/agent-facing projection;
- extreme contention;
- high-volume non-conflicting partitioned proposals;
- attempted private-state leakage.

## Performance watch item

Stage 1 must demonstrate partitionability without pretending Python-thread timing is distributed scalability. A genuine process-level or distributed/sharded workload remains required before Stage 10 freezes. Stage 1 must not freeze an interface that makes that later obligation require architectural reopening.

## Freeze rule

Stage 1 requires independent architecture review after qualification. No Stage-2 Matter/Materials expansion begins until Stage 1 is reviewed, decided, journaled, and frozen/closed.
