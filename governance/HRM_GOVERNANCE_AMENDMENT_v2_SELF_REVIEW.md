# HRM Governance Amendment v2 — Self-Review Replaces Independent Review

**Date:** 2026-09-23
**Amends:** HRM Master Development Plan v1.1, §8.1, as already amended by Amendment v1 (Review Policy)
**Authorized by:** project owner (instruction given in the Claude Code session of 2026-09-23: "We're not doing independent reviews anymore. Review yourself")

## Change

The review gate before a stage may freeze is now satisfied by a **self-review**: a review by the same Claude session that built or corrected the candidate. The separate-session requirement of Amendment v1 no longer applies.

The reviewer discipline from Amendment v1 stays in force:

- findings are labelled DIRECTLY VERIFIED, REPORTED/UNVERIFIED, RED or NOT TESTABLE;
- no fixes are made during the review pass;
- findings are frozen before the builder responds.

A RED finding still blocks freeze until it is corrected and the correction is verified.

## What this does and does not buy

**Does:** removes the wait for a separate session, so review and correction can happen in one working pass.

**Does not:** give any independence. The reviewer shares the builder's context, reasoning and blind spots, and has a stake in its own earlier work passing. This is weaker than Amendment v1, which at least removed shared conversational context. That limitation is accepted by the project owner and recorded here, so a "self-review: PASS" is not read as more than it is.

**Mitigation adopted:** self-reviews must attack the reviewer's own earlier changes first, and must show each regression test fails with its fix removed (mutation check), not only that it passes with the fix in place.

## Effect on the record

- Amendment v1 and every review already filed stand as filed. No earlier review is upgraded or downgraded by this amendment.
- The first review under this amendment is `reviews/HRM_STAGE1_SELF_REVIEW_2026-09-23.md`.
- This amendment changes who may conduct the review. It does not by itself freeze any stage; each stage's own exit criteria still apply.
