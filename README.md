# Human Resonance Model (HRM)

This repository is the **clean HRM rebuild**.

The June 2026 `hrm_core/` + `cognition_lab/` implementation was intentionally retired. It was built on the old entangled HRM kernel and is **not** a dependency, baseline, regression authority, or source of current behavioral evidence. Its commits remain recoverable in Git history only.

## Mission

Build an emergent human-population simulation in a consequential world without scripting the outcomes the model is supposed to discover.

## Current repository state

- **Stage 0 — Canon / Salvage Audit:** frozen/closed by the current governing record.
- **Stage 1 — Coordination Architecture:** active corrected implementation. Round-2 defects DAR-S1-004 through DAR-S1-006 have been corrected in code and regression-tested here. This repository does **not** claim the required independent freeze review has been supplied in the review chain currently stored here.
- **Stage 2 — Matter / Materials:** a self-tested Slice-A candidate is preserved under `drafts/stage2/`. It is quarantined from the active baseline until Stage-1 governance is formally satisfied.

- **Sandbox (exploratory, ungoverned):** `sandbox/` holds a runnable world simulation. It has terrain, seasons, plants, rabbits, and humans who learn by trial and by watching each other. It is for looking at behaviour now and is **not** qualification evidence. See `sandbox/README.md` and the proposed `governance/HRM_GOVERNANCE_AMENDMENT_v2_SANDBOX_TRACK.md`.

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

The HMT load/crash cards are intentionally heavy. On constrained tool hosts, run individual cards independently if the monolithic process hits a host execution limit; do not convert a host timeout into a model PASS or FAIL.

## Repository rule

Old HRM implementation code does not migrate forward merely because it existed. Reuse requires explicit evidence under the Stage-0 salvage rules.
