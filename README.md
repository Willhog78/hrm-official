# Human Resonance Model (HRM)

This repository is the **clean HRM rebuild**.

The June 2026 `hrm_core/` + `cognition_lab/` implementation was intentionally retired. It was built on the old entangled HRM kernel and is **not** a dependency, baseline, regression authority, or source of current behavioral evidence. Its commits remain recoverable in Git history only.

## Mission

Build an emergent human-population simulation in a consequential world without scripting the outcomes the model is supposed to discover.

## Current build focus — Genesis vertical slice

HRM's immediate implementation target is now the **smallest causally complete autonomous world**, not completion of every substrate stage in isolation.

The scientific destination is unchanged. The execution order is redirected so that Stage-1 coordination is exercised by a functioning world as early as possible:

1. integration contract;
2. physical substrate;
3. producer ecology;
4. consumer ecology;
5. autonomous ecological loop;
6. human biology;
7. cognition and memory;
8. general action and communication;
9. multi-population runs;
10. read-only emergence observer.

See `ROADMAP.md` for gates and exit criteria and `FILE_TREE.md` for the predetermined implementation structure.

The first major milestone is **Autonomous Computational Ecology v1**: a non-human world that can run for 100+ simulated years without scripted rescue, target-population correction, hidden food injection, or operator intervention.

## Current repository state

`STATUS.md` is the detailed record. This summary must agree with it.

- **Stage 0 — Canon / Salvage Audit:** frozen/closed by the current governing record.
- **Stage 1 — Coordination Architecture:** active corrected implementation, **not frozen**.
  - Round-2 defects, post-replacement defects C1–C6 and self-review defects F1–F5 are corrected and regression-tested. Under Governance Amendment v2, self-review replaces independent review.
  - A real pytest run passed on 2026-10-07 (43 + 14 tests; `evidence/STAGE1_PYTEST_RUN_2026-10-07.md`).
  - It is still not frozen: S1.12 lacks the `UPSTREAM/` archive, three reported risks are untested, and CI has never run.
- **Stage 2 — Matter / Materials:** a self-tested Slice-A candidate is preserved under `drafts/stage2/`. It is quarantined from the active baseline until Stage-1 governance is formally satisfied.
- **Genesis execution roadmap:** implemented through G10.7a step 4, with qualification assets for each phase:
  - G0–G10.2, then G10.2A survival affordances;
  - G10.3 capacities, G10.4 survival bottlenecks, G10.5 opt-in physiology;
  - G10.6 behavioural integrity;
  - G10.7a leak closure, witnessed memory, imitation and following.
  
  Long-run calibrated-human survival is not qualified.
- **Current focus:** cognition work is **paused** until the ecology question has been tested. The question is which condition denies social learning its opportunity: hunger, lack of reachable known food, nearby agents, or witnessed useful acts. See `docs/architecture/ECOLOGY_OPPORTUNITY_OPENING.md`.
- **Verification:** GitHub Actions has never run; every job is refused because the account is locked over billing. The local tiers and gate scripts are the verification record. See `STATUS.md`, "Verification infrastructure".

## Stage-1 architecture

The active coordination layer separates:

1. temporal orchestration;
2. deterministic transaction/arbitration;
3. provenance/replay evidence.

Causal kernels own their own state. Coordination operates through declared authority ports rather than private-state access.

### Round-2 corrections now enforced

- transaction IDs are unique across the run/replay domain;
- ledger epochs are admitted sequentially from persisted evidence, not trusted from the caller;
- all rejection-capable ledger admission/digest work occurs before causal materialization;
- prevalidated ledger evidence is finalized while legal readers remain blocked on the affected resource locks;
- imported/replayed evidence rejects duplicate historical transaction IDs and non-sequential epochs.

## Reproduce

Fast Stage-1 regression suite:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=src:. python -m pytest -o addopts='' -q tests/test_stage1_coordination.py
```

Hugh Mann Stage-1 Gate:

```bash
PYTHONPATH=src:. python qualification/hmt_stage1_gate.py
```

Genesis development loop (micro + smoke, about 30 s), a targeted diagnostic, and the social-learning opportunity census:

```bash
python -m qualification.genesis.tiers fast
python -m qualification.genesis.tiers diagnostic following
python -m qualification.genesis.opportunity --check-digest
```

The HMT load/crash cards are intentionally heavy. On constrained tool hosts, run individual cards independently if the monolithic process hits a host execution limit; do not convert a host timeout into a model PASS or FAIL.

## Repository rule

Old HRM implementation code does not migrate forward merely because it existed. Reuse requires explicit evidence under the Stage-0 salvage rules.
