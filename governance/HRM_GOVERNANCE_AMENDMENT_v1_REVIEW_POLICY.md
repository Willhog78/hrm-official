# HRM Governance Amendment v1 — Review Policy

**Date:** 2026-09-15
**Amends:** HRM Master Development Plan v1.1, §8.1 (Qualification and Freeze Cycle)
**Authorized by:** Will Hogan (project owner)

## Change

§8.1 previously required "independent architecture review" — reviewer status distinct from
dependent/internal — before foundational/high-coupling stages (Coordination Architecture,
Matter/Materials, Human Cognition, Social Learning/Reputation, Multi-Population Baseline,
Observer Layer) may freeze.

**This requirement is redefined, not removed.** A review satisfies the independent-review gate
if it is conducted:

1. by Claude, in a **separate chat session** from the one that built the candidate or ran the
   dependent review — no shared conversational context, no memory of the build reasoning; and
2. using the reviewer-rule discipline already established in Stage 1's reviews (DIRECTLY
   VERIFIED vs REPORTED/UNVERIFIED vs RED vs NOT TESTABLE; no fixes during the hostile pass;
   findings frozen before builder response).

## What this does and does not buy

**Does:** removes shared short-term context and the builder's in-session incentive to see their
own work pass. A fresh session has no stake in the prior session's conclusions and no memory of
"why" a design choice was made — it has to re-derive that from the artifacts, same as any
outside reviewer would.

**Does not:** substitute for a reviewer with a genuinely different training lineage, a human
domain expert, or an adversarial party with incentive to find flaws. Every review under this
policy remains, at the architecture/model level, the same underlying system reviewing its own
output. This is a known, accepted limitation — logged here rather than allowed to erode
silently into every future "independent review: PASS" meaning more than it does.

## Practical effect on the record so far

- Stage 1 Dependent Adversarial Review Round 2 (2026-09-15, same-session) stands as filed.
- Stage 1's required "independent" review may now be satisfied by a Claude review conducted in a
  new chat, using the Stage 1 review candidate package as the sole basis (no conversational
  carryover from this session). Until that review is run and filed, Stage 1 remains **ACTIVE**,
  freeze/close is **NO**, and Stage 2 authorization is **NO** — this amendment changes who may
  grant the freeze, not the fact that it hasn't been granted yet.

## Revocation

This amendment applies going forward from this date. It does not retroactively upgrade any
review already logged as "dependent-only."
