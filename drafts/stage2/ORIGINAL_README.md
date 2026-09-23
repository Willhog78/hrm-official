# HRM Stage 2 Slice A — Matter and Materials — Self-Built Candidate v0.1

**Honest status: NOT REVIEWED, NOT FROZEN.** This is a first implementation pass built and
self-tested in one sitting, following the entry-contract-before-code discipline the project
requires, but it has not been through the dependent/independent adversarial review cycle that
Stage 1 went through before freeze. Treat it as a draft for that process, not as a decided
architecture.

## Contents

- `STAGE2/HRM_STAGE2_ACTIVE_CONTRACT_v0.1.md` — predeclared M2.1–M2.10 exit criteria, written
  before implementation.
- `src/hrm_matter/` — implementation: `properties.py` (element data), `entities.py` (composition/
  mass/energy/phase model), `transform.py` (split/merge/heat with built-in conservation checks),
  `kernel.py` (ownership boundary, ported from the start using the Stage-1 Round-2 lesson).
- `tests/test_stage2_matter.py` — 25 tests covering every M2.x criterion plus two real findings
  from self-review (see journal).
- `JOURNALS/HRM_BUILD_JOURNAL_STAGE1_APPEND` equivalent for Stage 2:
  `JOURNALS/HRM_BUILD_JOURNAL_STAGE2_SLICE_A.md` — documents two real bugs found by running the
  suite (not by inspection) and one real state-integrity defect found by self-adversarial review,
  all corrected and reverified.

## Reproduce

```bash
PYTHONPATH=src python3 -m pytest tests/ -q
```

Expected: `25 passed`.

## What this deliberately does not include yet

Combustion, decay, fracture, and named chemical reactions (Slice B, per the active contract's own
scope discipline) — and integration with the Stage-1 `TransactionFabric` (Matter transformations
are not yet routed as `TransactionProposal`s through Stage-1 coordination; that wiring is the next
concrete step before this can be qualified as a true Stage-1-coupled kernel).
