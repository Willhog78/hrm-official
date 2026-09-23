# HRM Stage 2 Slice A (Matter and Materials) — Build Journal

## 2026-09-15 — Entry contract written before any implementation

`STAGE2/HRM_STAGE2_ACTIVE_CONTRACT_v0.1.md` was written first, scoping Slice A to the causal
substrate (real composition, mass/energy conservation, derived phase, generic split/merge/heat)
and explicitly deferring combustion/decay/fracture/named reactions to a separate Slice B contract,
per §10's vertical-slice discipline and the Stage-0 salvage ledger's own note that chemistry
expansion was assigned to a later Stage-2 pass.

## 2026-09-15 — Implementation, self-adversarial pass, two real defects found and corrected

First implementation pass (`properties.py`, `entities.py`, `transform.py`, `kernel.py`) plus a
25-case test suite covering M2.1–M2.10. Running the suite immediately (not after "looks correct"
inspection) surfaced two real defects:

1. **Placeholder element-property bug:** hydrogen's melt/boil thresholds were entered in the wrong
   order (259 > 20), which the `ElementProperties.__post_init__` invariant check correctly rejected
   at import time. Corrected to a physically-ordered placeholder (14 < 20). This is the kind of
   authored-constant error the Stage-0 salvage audit already flagged as a general risk category —
   caught here by the invariant firing, not by hand-checking the numbers.
2. **Test-design bug, not a kernel bug:** the fuzz test (M2.10) initially asserted total energy
   never changes across a random operation sequence that includes `add_energy` — but `add_energy`
   is a declared external source/sink by design, not a closed-system operation. The kernel was
   correct; the test's conservation law was wrong. Corrected to track injected external energy
   explicitly and assert the closed-system total changes by exactly that amount.

**Real finding, more serious than either of the above:** applying the same adversarial posture used
on Stage 1 to this module's own `port().get()`, a completely ordinary call — no reflection, no
tricks — showed that a caller could mutate the `.composition` dict returned by `get()` in place and
silently corrupt the kernel's real internal state. `frozen=True` on `MatterEntity` blocks reattaching
the `composition` attribute but not mutating the dict object it points to. This directly violates
M2.7 (state changes only through declared kernel operations) via ordinary code, not just reflection.

**Correction:** `composition` is now wrapped in `types.MappingProxyType` at construction, making it
genuinely read-only rather than merely relabeled. `canonical()` (used for hashing/serialization)
converts it back to a plain dict at that boundary only, where a copy cannot be used to reach back
into live state. Verified: the original attack now raises `TypeError`; full suite still 25/25.

**Boundary hardening applied proactively, not reactively:** `MatterKernel.port()` was built from the
start using the Stage-1 Round-2 lesson — operations are closures over local containers (`entities`,
`lock`, `id_box`), never over `self`/the kernel object — with a dedicated regression test
(`test_kernel_port_closures_do_not_resolve_to_a_kernel_object`) verifying no port method's closure
chain reaches a `MatterKernel` instance. The same documented residual-risk caveat as Stage 1 applies:
this is containment against accidental cross-boundary access, not a hostile-process guarantee.

## Current status

- Local suite: **25/25 passed**, including regression tests for both real findings above.
- Slice A exit criteria M2.1–M2.10: implemented and exercised by the suite, including an
  adversarial fuzz case (200-step random split/merge/heat sequence) and an exact-boundary phase
  case.
- **This is a self-built, self-reviewed candidate.** It has not yet been through the dependent or
  independent adversarial review cycle Stage 1 went through, and per the project's own governance
  rules, one builder's own testing is not sufficient for freeze. `qualification`-style standalone
  reproduction scripts and a locked HMT-style activation manifest (if Slice A is brought under the
  Hugh Mann Test framework, as Stage 1 was) are not yet built.

**Status: STAGE 2 SLICE A — IMPLEMENTED AND SELF-QUALIFIED — ADVERSARIAL REVIEW NOT YET PERFORMED — NOT FROZEN.**
