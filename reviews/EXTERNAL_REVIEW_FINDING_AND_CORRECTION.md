# External Review Finding — Closure-Based Private-State Leak (Round 2, external instance)

**Reviewer status:** External AI instance, no build-process access, no stake in outcome.
Not a human domain-expert audit. Findings below are from direct execution/inspection,
not from trusting prior claims.

## Finding

`StateAuthority.port()` (v0.2) built its `AuthorityPort` as a closure over `self`
(the whole `StateAuthority` instance). Standard, unprivileged Python reflection —
`bound_method.__func__.__closure__[0].cell_contents` — retrieved the live
`StateAuthority` object directly, and from there every private attribute
(`_StateAuthority__state`, in-flight transaction bookkeeping, test-only failure
injection hooks) in a single hop. This was not covered by the existing S1.6 test,
which only inspects `dir(port)` surface names.

This matters because "no private-state reads" is documented in the HRM Stage-0
salvage ledger as a core anti-entanglement invariant carried forward from Agentus,
and S1.11 requires private fields to "remain inaccessible through legal
coordination interfaces."

## Correction applied

`port()` now builds each of the six port operations as a closure over only the
specific private container(s) that operation needs (e.g. `snapshot` closes over
`state`/`versions` only; `stage_commit` closes over `staged`/`prepared`/the
bookkeeping lock/`inject_stage_failure` only), rather than over the whole
`authority` object. Verified: no port method's closure chain resolves back to a
`StateAuthority` instance (see new test
`test_s1_11_port_closures_do_not_expose_the_whole_authority_object`).

## What this fix does NOT claim

This is data-minimization / blast-radius containment, not elimination of
in-process introspection. CPython has no true in-process capability boundary —
`gc.get_referrers` can still walk to any live object, and each *mutating*
closure (`prepare`, `materialize_published`) still legitimately holds a live,
non-copied reference to the real `state` dict, because that is how it performs
its declared job. A sufficiently determined piece of code in the same process
can still reach and mutate that dict directly, bypassing versioning.

**This residual risk is accepted and documented, not hidden.** Closing it
completely requires a process/serialization boundary, which the Stage-1 active
contract already defers to the Stage-10 distributed/process-level work item.
Nothing in Stage 1's own kernels is adversarial; the realistic risk this
correction addresses is accidental cross-boundary access during Stage 2+
development, not a hostile co-resident kernel.

## Verification after correction

- Local suite: 34/34 passed (33 prior + 1 new regression test).
- HMT v0.2 Gate: 14/14 passed, unchanged locked manifest hash
  `2e8221abf363b57463d57732334ffa2d0568ea6d749eae00ee5f4a4673d76d35`.
- Preserved Agentus Gate-2 regression: 63/63 passed.
- No acceptance criterion was changed to obtain these results.
