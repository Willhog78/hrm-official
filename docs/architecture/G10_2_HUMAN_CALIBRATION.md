# G10.2 — Reference Human Calibration

## Purpose

Replace the Stage-1 qualification-scale human body with an opt-in reference-adult scale for long-run experiments.

## Guardrails

Calibration is opt-in and requires:
- 365 ticks per year, so one tick is one day;
- a material scale factor of at least 100;
- the existing G0-G9 causal stack.

The legacy qualification profile remains the default.

## Reference organism

G10.2 uses a neutral systems-model reference adult:
- total material mass: 70 kg;
- tracked dry mass: 28 kg;
- body water: 42 kg (60% of total);
- basal energy demand: 2,000 kcal/day;
- nominal water turnover: 2.5 kg/day;
- maturity: 18 years;
- maximum modeled age: 90 years;
- reproduction cooldown: 1 year.

These are reference parameters for systems experiments, not an individual medical model.

## Reduced chemistry caveat

Genesis still uses a reduced tracked-element basis inherited from the ecology layer. The 28 kg dry component is materially conserved but is not a full biochemical inventory of a human body.

## Exit condition

The calibrated mode must:
1. materially seed 70 kg founders without creating matter;
2. preserve a 60% reference water fraction at initialization;
3. use daily age and energy timing;
4. survive at least a 30-day integrated ecology run;
5. conserve tracked elements and water;
6. replay identically across checkpoints;
7. leave the Stage-1 default behavior unchanged.
