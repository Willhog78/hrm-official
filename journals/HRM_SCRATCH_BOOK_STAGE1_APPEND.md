# HRM Scratch Book — Stage-1 Append

**Authority:** NONE by itself. These are open questions, risks and observations, not approved architecture changes.

---

## 2026-09-11 — Post-publish infallibility is an adapter obligation

The atomicity protocol depends on a strict boundary: all potentially fallible work must happen before the publish barrier. After publish, each participant only materializes data that was already durably/legalistically staged.

Question for later kernel integration: can each real authority provide that staging/recovery guarantee cleanly? If a future adapter needs a fallible external side effect after publish, the current Stage-1 assumption is insufficient and should be treated as an architecture defect rather than papered over.

---

## 2026-09-11 — Partition routing policy remains deliberately generic

Stage 1 currently discovers conflict domains from `(authority_id, resource_id)` overlap. It does not decide that later kernels must partition by geography, entity type, space cell, or any other domain-specific rule.

When real kernels arrive, routing may need a stable ownership map. That map must preserve causal results when shards change and must not smuggle later-stage semantics into coordination.

---

## 2026-09-11 — Epoch evidence root versus distributed persistence

The replay ledger no longer requires a per-event global chain. There is still one deterministic epoch-root merge at synchronization boundaries. This looks compatible with partitioned causal work, but the independent reviewer should specifically attack whether the epoch-root merge, checkpoint rules, or evidence persistence could become a hidden system-wide bottleneck at much larger scale.

---

## 2026-09-11 — Process/distributed stress remains a real future obligation

The current build demonstrates dispatchable conflict domains and stable results under component-order permutations. It does not prove multicore/process/distributed throughput. The existing contract correctly keeps a genuine process-level or distributed/sharded stress test as an obligation before Stage 10 freezes.

Do not later cite the current Python timings as if that obligation had already been satisfied.

---

## 2026-09-11 — Same-epoch causal provenance is intentionally disallowed

Authoritative causal parents must already exist in prior-epoch evidence. This follows the explicit feedback-lag doctrine: proposals generated from `S_n` cannot truthfully claim causal dependence on another result that only becomes visible in `S_{n+1}`.

Worth attacking in review: whether any legitimate same-authority intra-interval process needs a richer composite-authority representation rather than weakening this rule.

---

## 2026-09-11 — Publication visibility is stronger than post-call atomicity

Round-1 correction work exposed an important distinction: checking state only after `resolve()` returns proves post-call atomicity, but not necessarily concurrent observational atomicity. Future transaction tests should include an observer racing the publication window, especially for cross-authority transactions.

This is a general coordination lesson, not a later-domain mechanism.

---

## 2026-09-11 — HMT caught a harness bug as well as architecture defects

The first locked Gate run failed deterministic replay even though every declared replay hash matched. The cause was an auxiliary Python tuple being converted to a JSON list in the clean-process result. Keeping that failed run is useful: hostile test infrastructure itself can act foolishly, and evidence packaging should distinguish a harness defect from a model defect rather than deleting the inconvenient run.

---

## 2026-09-11 — Resource-scoped publication locks appear to close the successful-publish observation window

The observer-race case intentionally pauses a cross-authority transaction after one participant has materialized. A legal projection of that already-materialized resource remains blocked until the whole transaction finishes because the writer still owns all transaction resource locks. This is stronger than the original post-call atomicity test and should remain a regression test when real kernels replace the synthetic authority fixture.

## 2026-09-23 — Host/process budget can contaminate monolithic qualification runs

The complete HMT sequence can exceed a constrained execution host's process/CPU budget after the heavy contention card even though the affected later cards pass when executed independently. Keep qualification evidence granular enough to distinguish model failure from harness/host exhaustion. Do not lower HMT thresholds to make a constrained host green.

## 2026-09-23 — Stage-2 contract provenance conflict

The supplied Matter Slice-A contract states that Stage 1 had already frozen after external review, but the supplied independent-review handoff says the independent review was still required before Stage-1 freeze and Stage-2 authorization. Until the actual freeze verdict is in the governing record, treat the Matter candidate as quarantined work rather than an authorized baseline.
