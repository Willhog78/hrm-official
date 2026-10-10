# Procedural frontier state recognition v1

## Boundary addressed

V4 sequence valuation and own adjacency use a physical projection that omits ordinary energy, water and fatigue bands but retains injury and every other perceptual field. The exploratory frontier previously matched raw before/after dictionaries, including all body bands. An agent could recognize a procedure for valuation yet fail to recognize the same material prerequisites for a second exploratory trial after ordinary bodily drift.

This change aligns only the frontier's remembered-before/current and successor-before/prior-after comparisons with the existing V4 projection. It neither expands physical generalization to changing weather/material nor supplies benefits to enabling acts. It does not make a new action available merely because it was remembered.

## Version and ownership

`GenesisConfig.agentus_frontier_state_enabled` defaults False and requires `experienced-transitions-v4` (whose existing validation requires capacities and size-scaled energy accounting). When enabled, canonical config records `agentus_frontier_state: procedural-frontier-v1` and human authority state records `frontier_state_model: procedural-frontier-v1`. Flag-off canonical fingerprints and behavior retain raw dictionary comparisons. Old modes remain available. Cross-version checkpoints are rejected by fingerprint validation.

Four runtime files change: config/runner declare the opt-in version; transitions exposes its existing read-only physical projection as `same_procedural_state`; interactions uses that comparison in the frontier. Physical execution, planning priorities, transaction boundaries, physiology, environmental configuration and production settings are unchanged. Qualification only adds an optional final argument to the existing discovery runner and a six-world comparison gate.

## Trial contract

- The candidate must be currently offered and already known in the actor's own action values.
- The actor must have its own remembered matching before-state with an outcome that enabled another interaction.
- Current energy must cover two basal ticks and available water above the floor must cover two water-loss ticks. These are recomputed at every choice.
- The existing frontier trial probability remains 0.12. Enabling an action is evidence for another experiment, not physiological reward or a mandatory instruction.
- All matching outcome counts contribute to the existing eight-attempt limit. Body variants share this budget instead of giving each variant eight trials. A positively credited, under-tested, actually remembered enabled successor permits the existing extra budget, capped at 16 attempts.
- Weather, access, position, available acts, held/ground/worn material, pool bands, geometry and injury remain exact at their existing perceptual resolution.
- No before/after record, benefit, predicted state, memory size or physical action allowance is changed by recognizing a candidate. Selected trials still pass through normal execution with actual effort, fatigue, injury and material constraints. The limit remains three interactions per tick.

Limits remain those of V4: coarse perceptual bands, bounded remembered outcomes, forgetting after 96 ticks, and state-dependent rather than lifetime trial budgets. The flag does not address changing weather, insufficient meaningful payoff, long sequences beyond six actions, or persistence/cultural inheritance. These remain empirical boundaries.

## Validation

Focused tests demonstrate body-drift recognition, unchanged flag-off behavior, physical mismatch rejection, reserve exclusion, absence/non-enabling rejection, unchanged trial probability, aggregate attempt limits and the finite positively experienced successor allowance. A complete observed 35-day run must match an unobserved 13+22-day checkpoint replay across all authorities and ledger, with physical action bounds intact.

`qualification/genesis/run_frontier_state_gate.py` runs three untrained active worlds and three flag-off worlds for 365 days. Flag-off fingerprints and ledger digests must exactly match captured incremental-interlacing worlds; all worlds must conserve matter/water/lithics and have valid chains. Active runs additionally count choices, real progress and thermal consequences. Physical/test success is not evidence of useful practice unless actual ecological outcomes demonstrate it.

```bash
PYTHONPATH=src:. python -m qualification.genesis.run_frontier_state_gate \
  --output experiments/genesis/summaries/FRONTIER_STATE_GATE_2026-10-10.json
```
