# Material work scale — 2026-10-09

**Incremental surface work is missing. Wood can produce meaningful protection, but useful scale requires many preparatory actions.** This controlled response audit isolates those physical/action boundaries without changing runtime code, reward, planning, configuration or live ecological state.

## What was measured

The probe calls the existing material and physiology functions on declared copies and fixtures. It tests 15 raw-weave combinations, 9 sequential joining combinations up to 64 joins each, 33 binary-twist combinations, and 54 mass/weather/orientation combinations. Results are reproducible and the source simulation snapshot and ledger remain unchanged.

These are controlled measurements, not agent decisions, demonstrations placed in memory, or autonomous discovery. Reference raw fibres use source-class midpoint dimensions and internally consistent dry mass. Their elemental input is a single-carbon mass fixture, not a claim about tissue composition. Full-length bark/tendon examples assume those dimensions have already been obtained; live bare-hand extraction shortens them. The separate twist-cost probe applies those bare-hand length reductions.

The response uses the production-arm adult physiology profile captured in the JSON. Thermal measurements compare one physiology step on two copies of the same initial body. Conditions are dry, 4 m/s wind, no fire or terrain cover, at 12, -5 and -20 °C. Arrangement measurements compare incident wind from 0, 90 and 180 degrees, with the occupant at the arrangement centre. Stored output includes both actual debits and cold-exposure changes. One-day savings and optimistic payback are not ecological lifetime returns.

## Woven-material boundary

`interlace` in live interactions consumes currently held raw strands, with at most six soft objects in hand. No live affordance adds strands to an existing surface. The lower material function accepts larger strand sets, so large raw weaves can be measured but cannot be made in one current live act.

| Reference raw fibre | Six-strand area | 100-strand area | 100-strand mass | Cold-day thermal saving at -5 °C |
| --- | ---: | ---: | ---: | ---: |
| Plant | 1.5876 cm² | 441 cm² | 47.84 g | 1.764 kcal |
| Bark | 5.76 cm² | 1,600 cm² | 347.15 g | 7.111 kcal |
| Tendon | 2.8224 cm² | 225 cm² | 30.02 g | 0.700 kcal |

The 100-strand rows are low-level material-response fixtures, beyond live hand capacity. They establish a possible physical response; they do not establish attainable manufacture or repayment of total work. At 12 °C all these reference surfaces saved zero thermal energy because the bodies were already within the modeled comfort band.

The six-object limit is not an absolute surface-area ceiling. Existing twisting can consolidate many raw fibres into six thick bundles. In the sampled bare-hand binary-twist route, the best plant result within the carrying limit needed 1,536 raw strands for 334.70 cm², with an optimistic 21,481 kcal of successful extraction, twisting and interlacing. The best bark result used 384 raw strands for 326.49 cm² at 9,961 kcal. These calculations exclude storage, pickup, failures, decay, feeding, travel and wearing. Tool-assisted preparation could change the extraction cost and dimensions. The inefficient existing route must not be mistaken for physical impossibility.

## Joining boundary

With full-length midpoint reference fibres and no decay, sequential plant-patch joining using plant binders succeeded twice and failed on the third attempt: cohesion fell from 0.9 to 0.675 to 0.50625, then below the 0.5 acceptance threshold. The resulting three-patch area was 4.44528 cm². All inputs of successful joins conserve their elements.

Bark binders retained cohesion across all 64 tested joins. That is the search limit, not an unlimited-success claim. Joining 65 six-strand bark patches produced 337.536 cm² at 542.72 kcal of joining effort alone; patch production and binder acquisition were excluded. This demonstrates another existing accumulation route, not an economical manufacturing result. The untrained PR #46 worlds offered zero complete joining opportunities, so acquisition of two unworn held surfaces and a binder remains separate from join physics.

## Arrangement boundary

The wood fixture starts with 100 kg of local wood. Existing `apply_force` transfers 0.25 kg per action; one final `arrange` shapes the accumulated loose material at the maker's position. Actual primitive costs and surviving-mass geometry limits are used. This optimistic batch omits intervening material decay, fatigue suppression, biological priorities, feeding, transport and learning. Its sequence is diagnostic input only.

| Arranged kg | Preparation kcal | Actions | Minimum ticks at 3 actions/tick | Thermal saving per -5 °C day | Optimistic repayment days after preparation |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.25 | 21.75 | 2 | 1 | 0.001504 | 14462.3 |
| 1 | 63 | 5 | 2 | 0.061111 | 1030.9 |
| 5 | 283 | 21 | 7 | 1.527778 | 185.2 |
| 15 | 833 | 61 | 21 | 13.750000 | 60.6 |
| 30 | 1658 | 121 | 41 | 49.500000 | 33.5 |
| 60 | 3308 | 241 | 81 | 49.500000 | 66.8 |

The 30 kg result produces 2 m² of effective surface under the existing mass constraint. It is physically consequential under favourable incident wind. Sixty kg doubles preparation cost but provides no additional benefit in that row because the existing protection model saturates. Turning the face away eliminates this modeled wind-facing contribution. These values describe the current coarse model, not validated real-world construction physics.

The four-to-six-action learned planning horizon is much shorter than the 121 preparatory actions in the 30 kg fixture. That mismatch merits a later controlled procedural test. This audit does not establish that a longer horizon would solve discovery, or that the measured optimistic return survives ecology, weathering and reserve guards.

## Concrete next change

Expose incremental interlacing on existing physically accessible surfaces: add currently available strands over successive costed actions, while preserving actual material inventories, hand limits, old wear, cohesion and the existing material geometry. Preserve the earlier behavior through an explicit version option. Qualify growth, mass conservation, unsuccessful work, and measured thermal response before untrained ecological testing.

Keep arrangement development active alongside fibres. Measure actual accumulated work and material loss under normal ticks at consequential mass, then test whether own observed progress can support repeated investment. The current result supports this controlled test; it does not justify raising protective strength or skipping preparation.

## Validation and reproduce

All three diagnostic tests passed. They check source-state isolation and exact reproducibility, conservation, the distinction between raw hand limits and consolidation, seam failure bounds, directional thermal response and the three-action tick lower bound. Maximum measured join element error was 8.66e-15 kg; wood transfer errors were below 1e-9 kg. `git diff --check` passed.

```bash
PYTHONPATH=src:. python -m qualification.genesis.material_scale --output experiments/genesis/summaries/MATERIAL_SCALE_2026-10-09.json
PYTHONPATH=src:. python -m pytest -q tests/genesis/test_material_scale_diagnosis.py
```

The complete fixture parameters, captured physiology profile and measurements are in `MATERIAL_SCALE_2026-10-09.json`. No runtime source code or production settings changed in this diagnosis.
