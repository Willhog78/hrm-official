# HRM Stage 1 — Predeclared Qualification Plan v0.1

This file binds the active contract to concrete evidence before independent review.

| Criterion | Evidence path |
|---|---|
| S1.1 deterministic scheduling/replay | `test_s1_1_deterministic_enumeration_and_worker_order` |
| S1.2 explicit multi-rate time | `test_s1_2_explicit_multirate_scheduling` |
| S1.3 stale-read rejection | `test_s1_3_stale_read_rejected` |
| S1.4 deterministic conflicts | `test_s1_4_conflict_arbitration_order_invariant` |
| S1.5 local atomicity | `test_s1_5_local_atomic_transaction_failure_leaves_no_partial_state` |
| S1.5 cross-partition atomicity | `test_s1_5_cross_partition_mid_commit_failure_has_zero_partial_observable_commit`; repeated hostile sweep in benchmark evidence |
| S1.6 authority ownership | private-port and unknown-authority tests |
| S1.7 provenance/replay | replay completeness + chain/block verification tests |
| S1.8 feedback lag | same-epoch read test |
| S1.9 partitionability | 64-domain load; explicit conflict-domain plan; reversed component-execution test |
| S1.10 contention scaling | 1k/5k/10k/25k contention and partitioned-load sweeps |
| S1.11 hostile encapsulation | private-state interface test |
| S1.12 baseline regression | preserved Agentus Gate-2 suite reproduced from frozen upstream |
| S1.13 provenance separation | fallible-projection test + malformed provenance hostile test |
| S1.14 fresh-process restart | checkpoint/subprocess continuation test |

No performance threshold is invented after seeing the data. The scaling obligation is to expose the measured curve, preserve failures, and reject hidden algorithmic collapse rather than to claim a universal throughput number from one machine.
