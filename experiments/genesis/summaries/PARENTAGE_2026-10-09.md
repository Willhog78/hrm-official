# Agentus parentage and ancestry — 2026-10-09

The birth gate previously checked only for an adult male in the mother's cell. It never selected a father, and a child's caregiver could be reassigned. Caregiver identity is therefore insufficient to reconstruct biological ancestry. Legacy runs have no recoverable paternal identity.

## Implemented contract

`agentus_parentage_model="recorded-pair-v1"` opts into deterministic modeled pairing and a persistent parentage register. The default remains `none`; existing fingerprints and state shapes omit these fields. Observer/replay arm: `v1-remainingmilk-reservepredators-searchpredators-parentage`, stacked on the search arm from PR #37.

For every actual birth, the mother is the individual paying the existing birth costs. The father is the lexicographically lowest-ID living mature male in that same cell after the day's movement and deaths. The register stores all eligible male IDs and the selection policy. This is a declared pairing convention, not a mate preference, courtship model, or recovered biological fact about earlier runs. Multiple females may pair with the same male; no new male energy or cooldown gate is introduced.

Each living individual receives immutable `mother_id`, `father_id` and `birth_epoch` fields. The authority's `lineage` register retains one compact record for every seeded founder and actual birth, including death epoch. Founders' parents and birth epochs remain unknown (`null`). Maternal and paternal ancestors are traversed through this register, including dead parents; ancestor lists are derived rather than duplicated in every individual. Retention grows with the number ever born so old ancestry is not silently lost. Caregiver reassignment does not rewrite parentage.

The existing generation label remains mother generation + 1. It is not reinterpreted as depth on both sides. The new metadata does not enter Agentus perception, memory, planning, physiology or birth eligibility. Relationship diagnostics distinguish parent/child, ancestor/descendant, full and half siblings, and shared ancestry. `no_recorded_relation` means no relation found in this incomplete register, not proof of genetic unrelatedness. Kinship does not block births, and no inherited genetic consequences or genetic viability are claimed.

Canonical checkpoints preserve the register and reject a mismatching configuration. The private diagnostic also refuses to resume a legacy snapshot under the new parentage arm. Paternity must be recorded by a fresh run; it is never backfilled from current neighbors.

## Four-seed ten-year comparison

| Seed | Humans alive | Actual births | Human deaths | Retained records | Complete physical-state equality |
|---|---:|---:|---:|---:|---|
| a | 21 | 13 | 0 | 21 | Pass |
| b | 29 | 21 | 0 | 29 | Pass |
| c | 18 | 10 | 0 | 18 | Pass |
| d | 48 | 40 | 0 | 48 | Pass |

All 84 births have both parents recorded, and all 32 founders retain unknown parents. Twenty-six births have two eligible males; the declared tie rule is recorded rather than hidden. Removing ONLY the model/register fields and the three per-person parentage fields gives exact equality of all five final world, matter, producer, consumer and human states against the preceding search runs. Every annual record also matches except elapsed wall time. Final-state canonical hashes and all birth registers are saved in the evidence JSON. Cross-arm ledger digests differ because configurations and causal state differ; that is expected.

## Year-20 continuation of C

The matching year-10 private snapshot was resumed through year 20. Every existing parentage record was preserved. Final human results: 28 alive, 20 cumulative births, 0 deaths; generation counts {'1': 20, '0': 8}. No generation-2 humans appeared in this continuation. Multi-generation traversal on both sides is verified by regression fixtures; it is not inferred from this seed. The continuation is an ancestry check, not a new twenty-year on/off comparison.

Actual births after the resume:

| Child | Mother | Selected father | Maternal generation | Epoch | Recorded parent relationship |
|---|---|---|---:|---:|---|
| human-b00000018 | human-g00000006 | human-g00000003 | 1 | 3695 | no_recorded_relation |
| human-b00000019 | human-g00000006 | human-g00000003 | 1 | 4060 | no_recorded_relation |
| human-b00000020 | human-g00000006 | human-g00000003 | 1 | 4425 | no_recorded_relation |
| human-b00000021 | human-g00000006 | human-g00000003 | 1 | 4790 | no_recorded_relation |
| human-b00000022 | human-g00000006 | human-g00000003 | 1 | 5155 | no_recorded_relation |
| human-b00000023 | human-g00000006 | human-g00000003 | 1 | 5520 | no_recorded_relation |
| human-b00000024 | human-g00000006 | human-g00000003 | 1 | 5885 | no_recorded_relation |
| human-b00000025 | human-g00000006 | human-g00000003 | 1 | 6250 | no_recorded_relation |
| human-b00000026 | human-g00000006 | human-g00000003 | 1 | 6615 | no_recorded_relation |
| human-b00000027 | human-g00000006 | human-g00000003 | 1 | 6980 | no_recorded_relation |

All newly recorded children include their complete known maternal and paternal ancestor sets in the continuation summary. Selection remains the declared lowest-ID rule, and birth eligibility is unchanged even if relatives qualify. The continuation's older predator birth-event list is incomplete because the existing diagnostic does not restore that external callback counter; predator ancestry is outside this change. Human parentage is retained inside saved causal state and is complete.

## Validation

- Full final suite: 371 passed, zero errors/failures/skips in 252.667 seconds, verified from saved JUnit. Individual case records are included in the evidence JSON.
- Fifteen new regressions cover real birth contact after movement, dead/immature candidates, deterministic multiple-candidate pairing, both sides of ancestry after death, paternal half siblings, related-pair recording, caregiver reassignment, malformed cyclic input, unavailable paternity, opt-in fingerprints, perception isolation, and canonical checkpoint/resume with an actual recorded birth already present at the checkpoint.
- Three-seed × 75-day combined-arm smoke: zero failures/warnings; valid ledgers, identical observed/unobserved digests and maximum relative element error approximately 1e-15.
- All four fresh ten-year runs pass complete 30-day canonical scheduler-state equality before and after diagnostic instrumentation.
- With parentage off, the updated human kernel matches its parent on every complete human/producer/matter/consumer state over four years at both 12 and 365 ticks/year (48 + 1,460 steps).
- The legacy private-snapshot resume guard rejects unavailable historical paternity. The new C continuation preserves all prior parentage records.

## Reproduce

```sh
python -m pytest tests/genesis/test_parentage.py
python -m qualification.genesis.tiers smoke --arm v1-remainingmilk-reservepredators-searchpredators-parentage --days 75
python experiments/genesis/run_generations_diagnosis.py --seed c --arm v1-remainingmilk-reservepredators-searchpredators-parentage --years 10 --owned-state --spatial-index --out runs/parentage
python experiments/genesis/run_generations_diagnosis.py --seed c --arm v1-remainingmilk-reservepredators-searchpredators-parentage --years 20 --owned-state --spatial-index --resume-state runs/parentage/c-state-y10.json --out runs/parentage/c-20
```

Repeat the ten-year command for a, b and d. Default models, production Railway settings and original checkpoints are unchanged. No deployment or merge was performed.
