# HRM Build Journal — Stage-1 Append

**This is a chronological append to the authoritative Build Journal carried by the v1.5 baseline. It does not replace the earlier Stage-0 record.**

---

## 2026-09-11 — Stage 1 opened under corrected entry contract

Stage 1 began only after Stage 0 had been frozen/closed and the Stage-1 entry contract had been corrected to include the missing cross-partition atomicity torture case. The active scope was held to three things: Temporal Orchestrator, Transaction/Arbitration Fabric, and Provenance/Replay Ledger.

No Matter, climate, ecology, cognition, social-system, technology, institution, or observer implementation was added for convenience.

**Meaning in plain language:** this stage is building the traffic rules and receipts for future causal kernels, not building any of the world itself.

---

## 2026-09-11 — Cross-partition atomicity design chosen and implemented

The central Stage-1 blocker was how to let one transaction touch more than one independently owned partition without either exposing half a result or solving the problem with one giant global lock.

The implemented approach uses non-visible prepare/stage state plus a publish barrier. Every participant validates and stages its local write first. A staged write is not visible. If any participant fails during that commit path, all participants abort. Only after every participant has staged successfully is the transaction published and locally materialized.

The hostile unit test deliberately lets authority A stage, then forces authority B to fail. Both authorities remain at their original observable values and versions.

**Meaning in plain language:** one side is allowed to get ready first, but nobody is allowed to show the result until everybody is ready. If one side breaks, the other side throws its prepared result away.

---

## 2026-09-11 — First Stage-1 unit suite passed

The first complete Stage-1 test suite passed its deterministic scheduling, multi-rate timing, stale-read, arbitration, atomicity, authority-boundary, replay, feedback-lag, provenance-separation and fresh-process restart cases.

This was treated as evidence that the architecture was functioning, not as permission to freeze the stage.

---

## 2026-09-11 — Scaling defect found in provenance validation and corrected

Before running the large contention sweep, source inspection found that the ledger's provenance validator rebuilt the full set of prior transaction IDs during every append. Small tests hid the problem, but long runs would make that path unnecessarily quadratic.

The implementation was changed to maintain indexed sets of known record IDs and transaction IDs incrementally. The unit suite was rerun and remained green.

**Meaning in plain language:** we found the kind of problem that often survives toy tests and only becomes painful after the simulator gets big. It was fixed before accepting load-test evidence.

---

## 2026-09-11 — Global replay-chain bottleneck risk removed

The first replay ledger used one global event-by-event hash chain. That was deterministic, but it made every evidence record wait conceptually on the preceding record and weakened Stage 1's no-global-bottleneck objective.

The ledger was redesigned around epoch evidence blocks. Every valid proposal in an epoch can be hashed independently against the previous epoch root. The record digests are then sorted and combined into one deterministic epoch root. Replay remains exact, but unrelated causal work does not need one per-event serial evidence chain.

The tests and scaling sweeps were rerun after the redesign and remained passing.

---

## 2026-09-11 — Partitionability made explicit rather than implied

The fabric now discovers independent conflict domains from resource overlap. Non-conflicting components can execute in different permutations without changing final causal state, arbitration digest, or replay digest. A dedicated hostile test reverses component execution order and gets the same result.

This does not claim Python-thread speedup or distributed throughput. It establishes the architectural seam needed for later process/sharded execution.

---

## 2026-09-11 — Empty-epoch replay ambiguity caught and corrected

During the packaging/reproducibility pass, an edge case was found in the epoch-segmented replay design. If an epoch contained no valid committed proposal, the replay root could remain unchanged. That would make “the simulation advanced through an empty/rejected epoch” indistinguishable in the evidence root from “that epoch never happened.”

The ledger now emits a deterministic epoch evidence block even when the epoch has no committed records. A hostile test confirms the replay root advances while causal state remains unchanged.

**Meaning in plain language:** doing nothing for one tick is still part of the experiment's history, and the replay record now proves that tick actually happened.

---

## 2026-09-11 — Internal Stage-1 qualification evidence assembled

The final current unit suite reports **19 passed, 0 failed**.

The scaling sweeps completed at 1,000 / 5,000 / 10,000 / 25,000 proposals for both maximal single-resource contention and ordinary partitioned load. The 25,000-proposal runs completed without the earlier style of superlinear collapse. A repeated cross-partition hostile sweep executed 400 spanning transactions with 58 injected commit-path failures and no partial observable commits.

The preserved Agentus Gate-2 pytest suite was also rerun from the frozen upstream archive: **63 passed, 0 failed**.

Compile checks passed.

**Meaning in plain language:** the Stage-1 mechanisms now have a real implementation and a meaningful torture suite behind them. They are not frozen yet. The next governance step is independent adversarial architecture review.

---

## Current Stage-1 status

`QUALIFICATION EVIDENCE PASS — INDEPENDENT ADVERSARIAL REVIEW PENDING`

No freeze/close declaration has been made. No Stage-2 work is authorized by this result alone.

## 2026-09-11 — Dependent adversarial review Round 1 failed and findings frozen

A dependent/internal hostile review was performed against the Stage-1 pre-freeze gap audit. The reviewer explicitly did **not** treat prior builder claims as verified evidence. The round returned:

`FAIL / NOT REVIEWABLE TO COMPLETION`

Three blocking findings were frozen before correction work began:

- **DAR-S1-001 — incomplete review package:** the reviewer had only the gap audit, not the actual candidate ZIP, HMT book, master plan, raw evidence, environment data, or hashes.
- **DAR-S1-002 — HMT execution contract not locked:** the Stage-1 Hugh Mann activation/execution manifest had not been predeclared before scored runs.
- **DAR-S1-003 — HM-S01-08 red:** the diagnostic showed eight independent domains still passing through a serial component-dispatch loop (maximum simultaneous active work = 1; elapsed approximately equal to the 0.160 s serial floor).

The reviewer also marked HM-S01-10, HM-S01-12, HM-S01-13 and HM-S01-14 missing, and several other cards incomplete or unverified under the HMT v0.2 execution rules.

**Decision:** Stage 1 remains ACTIVE. It is not frozen or closed. The v0.1 review candidate is retained as historical pre-HMT evidence and is not the final Stage-1 review candidate.

**Meaning in plain language:** the first build had useful machinery and tests, but it had not yet earned the right to be called Stage-1 complete. The hostile review caught both an evidence-packaging failure and a real serial choke point.

---

## 2026-09-11 — Atomic-observability gap discovered during Round-1 handback

While preparing the Round-1 corrections, source inspection found a stricter atomicity issue than the original forced-stage-failure test exercised. The old publish sequence made staged writes invisible and correctly rolled back pre-publish failures, but after the publish decision it materialized participant A and then participant B sequentially. A concurrent legal observer using the fabric projection API could theoretically read A after A materialized but before B materialized.

This was not observed in the original post-resolution tests, but it violates the intended phrase **zero partial observable commit** if observation is allowed concurrently with publication.

**Correction direction chosen before confirmatory HMT runs:** add resource-scoped publication locks held across prepare → stage → publish → materialize, and make legal projections acquire the same resource locks. Locks are scoped to the exact resources touched by a transaction, so unrelated conflict domains remain independently executable; no universal state lock is introduced.

**Meaning in plain language:** the first design prevented a failed transaction from leaving half a result behind, but it did not fully stop someone from peeking during the tiny interval while a successful multi-owner result was being made visible. The correction closes that window without putting the whole simulator behind one lock.

## 2026-09-11 — Locked HMT Stage-1 Gate Run 1: 13/14, failed HM-S01-01 due to harness representation mismatch

After the HMT v0.2 activation manifest was locked, the first scored 14-card Stage-1 Gate run was executed and preserved as `EVIDENCE/HMT_STAGE1_GATE_RUN1.json` plus stdout/stderr/exit-code evidence.

Result: **13 PASS / 1 FAIL**.

The previously red **HM-S01-08 Global Bottleneck Challenge passed** the locked criterion: 8 simultaneous active domains were observed, elapsed time was approximately 0.0225 s against a 0.160 s serial floor, and measured serial-floor speedup was approximately 7.11x. This is evidence that the Round-1 serial component-dispatch defect was actually removed rather than papered over.

The only failing card was **HM-S01-01 Deterministic Replay**. Diagnosis showed that all declared replay metrics were in fact identical across in-process and clean-process runs: state hash, ledger-export hash, replay root, and arbitration-digest sequence all matched. The harness nevertheless marked the card failed because it also directly compared an auxiliary Python `terminal_state` object containing tuples with the JSON-decoded clean-process form containing lists.

This is a **test-harness representation defect**, not a relaxation of the HMT criterion and not a model replay divergence. The failed scored run is retained. The correction is to canonicalize the auxiliary state representation (or compare only the already locked hash/digest metrics) and rerun the complete Gate battery under the unchanged manifest.

**Meaning in plain language:** the test caught its own bookkeeping mistake. The actual replay fingerprints matched exactly; Python tuples became JSON lists across the process boundary and the harness treated that harmless serialization difference as a simulation failure.

## 2026-09-11 — Locked HMT Stage-1 Gate Run 2: 14/14 PASS

After correcting only the HM-S01-01 harness serialization comparison, the entire locked HMT Stage-1 Gate battery was rerun under the unchanged activation manifest.

Result: **14 PASS / 14 total**.

Notable evidence from the scored run includes:

- **HM-S01-05 Atomic Rollback:** all 6/6 declared prepare/stage failure positions across a three-authority transaction returned to exact pre-transaction state; the concurrent observer case remained blocked during the deliberately widened partial-materialization window and observed only the completed state.
- **HM-S01-07 Contention Load:** all 120 seeded load runs passed exact accounting/correctness; no invariant violations were recorded.
- **HM-S01-08 Global Bottleneck Challenge:** 8/8 independent domains were simultaneously active; elapsed time was approximately 0.0236 s against the locked 0.160 s serial floor, approximately 6.77x serial-floor speedup.
- **HM-S01-11 Crash-and-Replay:** all 8 declared process-kill points recovered from the last clean checkpoint to the exact uninterrupted terminal state and replay root with no lost or duplicate events.
- **HM-S01-13 Fairness Under Symmetry:** 1000 frozen seeds produced contender-A win rate 0.528; forward-order subgroup 0.524 and reverse-order subgroup 0.532, all inside the predeclared bounds.
- **HM-S01-14 Mutation: Break the Arbiter:** the unmutated control passed 20/20 and the first-enumerated-wins mutant was killed 20/20 (100% kill rate).

The prior 13/14 scored failure remains preserved beside this passing run.

**Status consequence:** the HMT v0.2 Stage-1 qualification battery is now passing, but Stage 1 is **not frozen or closed**. The next governance step is a new adversarial review against the corrected, complete, immutable candidate package. Because the existing Round-1 review was dependent/internal and occurred before qualification completed, it cannot substitute for the required final architecture review.

**Meaning in plain language:** all fourteen tests we agreed to before scoring now pass without changing the rules after seeing the results. That earns a review candidate, not a freeze.

## 2026-09-11 — Final reproduction pass caught a package import defect

During the final clean-package verification, `PYTHONPATH=src pytest -q tests` failed during collection of `tests/test_stage1_hmt_contract.py` because the reviewer-facing thin wrapper imported `qualification.hmt_stage1_gate` but the package did not expose `qualification` on the pytest import path.

The standalone scored HMT Gate script remained valid and had already produced the preserved 14/14 scored Run 2, but the package-level reviewer command was not cleanly reproducible. This is treated as a packaging/reproduction defect rather than ignored.

**Correction:** make `qualification` an explicit package and include the package root in pytest's declared python path. Then rerun the complete package verification commands.

**Meaning in plain language:** the tests worked, but one of the advertised ways a reviewer would rerun them did not. A review package that cannot reproduce its own test command is not ready, even if the underlying code is good.

## 2026-09-11 — Reviewer pytest teardown hang traced to external ddtrace plugin

After the qualification import-path correction, all HMT wrapper tests reached PASS but the pytest process did not terminate in the current container. Isolation showed the package tests themselves completed; rerunning the same HMT wrapper suite with the externally auto-loaded `ddtrace` pytest plugin disabled exited normally.

The project does not require ddtrace. To make the advertised reviewer command deterministic against this environment, pytest configuration now disables that unrelated plugin with `-p no:ddtrace`.

This does not change any HMT test, threshold, model behavior or scored evidence.

## 2026-09-11 — Reproduction-helper hardening introduced and then exposed an indentation typo

While changing the clean reproduction lane to disable unrelated third-party pytest plugin autoload, an indentation/variable typo was introduced into `qualification/reproduce_stage1.py`. The next attempted reproduction run failed immediately with `IndentationError` before any evidence could be accepted.

The typo was corrected and the failed attempt is not counted as passing evidence. The clean reproduction command is rerun from scratch below.

## 2026-09-11 — Corrected Stage-1 v0.2 review candidate prepared

After the locked HMT Gate passed 14/14, the current package was rerun through its reviewer-facing test tree and upstream regression lane.

Final pre-package verification recorded:

- current Stage-1 test tree: **33 passed, 0 failed**;
- locked HMT Stage-1 Gate: **14/14 PASS** on scored Run 2, with scored Run 1's 13/14 failure preserved;
- preserved Agentus Gate-2 regression: **63 passed, 0 failed**;
- 25,000-proposal contention and partitioned-load sweeps completed correctly;
- repeated 400-transaction cross-partition hostile sweep retained 58 forced failures with zero residual partial commits;
- compile and supporting scope scans passed;
- clean reproduction helper reached `STAGE1_REPRODUCTION_PASS` with exit code 0.

Packaging/reproduction problems discovered during this pass—the missing `qualification` import path, an unrelated ddtrace pytest teardown hang, and a temporary indentation typo introduced while hardening the reproduction helper—were preserved in this journal and corrected before packaging.

The exact Hugh Mann Test v0.2 book, Master Development Plan, Round-1 dependent review, gap audit, locked activation manifest, raw HMT Run 1/Run 2 evidence, environment information, current source/tests and the old v0.1 candidate are all included or clearly marked historical.

**Current status:** `QUALIFIED REVIEW CANDIDATE v0.2 PREPARED — ADVERSARIAL REVIEW PENDING — NOT FROZEN / NOT CLOSED`.

No Stage-2 work is authorized.

## 2026-09-23 — GitHub source-of-truth replacement and Round-2 blocker correction

The public `hrm-official` repository was found to still contain the obsolete June cognition-era HRM kernel. That implementation is not carried forward. The repository replacement is built from the post-Stage-0 coordination line instead.

The supplied Round-2 dependent review was rechecked against the candidate source and its three blocking defects were still present in that uploaded source: historical transaction-ID reuse, caller-trusted persisted epochs, and ledger admission after causal materialization.

Corrections were applied without restoring any old HRM kernel code. Permanent hostile regressions were added for all three defects. The Stage-1 coordination regression suite passes 24/24. All fourteen HMT Stage-1 cards pass in constituent execution. The constrained tool host could not complete the monolithic HMT process after the load card, so that timeout is retained as a host limitation and not promoted into pass evidence.

**Governance consequence:** engineering correction is not self-freeze. Stage 1 remains active in this repository until the required independent review verdict is actually present in the record.
