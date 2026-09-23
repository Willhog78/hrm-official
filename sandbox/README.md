# HRM Sandbox

A runnable world simulation for **looking at behaviour now**, while the governed stages
(Stage 1 → Stage 13) continue on their own track.

**Status: exploratory. Nothing produced here is qualification evidence for any HRM stage.**
Sandbox code is not imported by `src/`, `qualification/`, or `tests/`, and governed code does
not depend on it. See `governance/HRM_GOVERNANCE_AMENDMENT_v2_SANDBOX_TRACK.md`.

## What it simulates

- **Terrain:** 64×40 grid from value noise: water, grass, forest, rock.
- **Seasons:** 200-tick year. Berries grow in spring and summer and spoil in winter. Nut trees drop
  hard-shelled nuts in autumn, and those nuts last into winter. Rabbits breed less and die more in winter.
- **Objects:** property bundles (hardness, sharpness, length). Stones, sticks, nuts.
  - Striking a hard object with another hard object can fracture off a sharp fragment.
  - Binding two objects combines their properties.
  - Nothing is labelled as a tool.
- **Humans:** hunger, thirst, ageing, death, reproduction, and nursing of infants. Each person perceives
  only a 5-cell radius and remembers the water, bushes and nut spots they have seen.
- **Learning:** each person holds `Q[(held-object signature, verb, target)]`, the expected
  food from doing that. It updates by TD(0) from:
  - their own attempts;
  - watching someone within 3 cells, gated by attention and familiarity.

  Every time a person comes to value a behaviour, the observer records whether they worked it out or
  who they learned it from.
- **Grouping:** a person's origin band is a display label only. Who people stay near is driven by
  familiarity built from time spent close together.
- **Observer:** read-only. It names behaviours after the fact from whatever keys people came to
  value. It has no predefined technique list.

Innate priors are limited to bare-hand attempts at rabbits and nuts. Everyone starts with no
object knowledge.

## Run

```bash
cd sandbox
python -m hrm_sandbox.run --seed 2 4 5 --ticks 6000 --out out/runs.html
```

This prints a summary per seed. It writes `out/runs_seed<N>.json` and one self-contained
`out/runs.html` viewer: a map playback, population and behaviour charts, and the learning log. It
uses the standard library only; 6000 ticks takes about 10–35 s per seed.

Tests:

```bash
cd sandbox && python -m pytest -o addopts='' -q tests
```

## Known simplifications (deliberate, sandbox-only)

- Time is compressed: adulthood at 500 ticks, old-age risk from 2400.
- Physics is coarse: nut cracking is hardness × force against shell hardness, and catch chance is linear in
  sharpness and length.
- There is no temperature, disease, injury, language, or durable records.
- One held object per person; no carrying of food.
- The "known" threshold (Q ≥ 7) is an observer convention, not a model quantity.
