# G10.1 — Scaled Substrate

## Purpose

Increase world and material scale without changing the already-qualified Stage-1 default.

## Design

`material_scale_factor` defaults to `1.0`. Existing G0-G9 runs therefore remain unchanged and reproducible.

A larger value scales:
- environmental elemental pools;
- surface and soil water inventories;
- initial producer biomass.

The first G10.1 qualification uses:
- a 32×32 world;
- `material_scale_factor = 1000.0`;
- the complete G0-G9 stack.

## Why this comes before realistic human anatomy

The Stage-1 ecology was intentionally tiny. A realistic adult body cannot be inserted honestly until enough conserved matter, food biomass, and water exist to support it.

G10.1 expands the substrate first. It does **not** claim the humans themselves are calibrated yet.

## Exit condition

The expanded world must:
1. preserve element and water accounting;
2. retain plants, animals, and humans;
3. provide each founder region enough local conserved biomass and water reserve for later adult-scale calibration;
4. keep the Stage-1 default unchanged.
