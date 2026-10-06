# Genesis Causal Contract

## Status

G0 integration contract.

## Purpose

Genesis connects the HRM Stage-1 coordination foundation to later causal world kernels without allowing coordination to become the owner of world semantics.

## Contract

1. Stage-1 coordination owns logical scheduling, transaction/arbitration, replay evidence, and checkpoint coordination.
2. Genesis domain kernels own their own causal state.
3. Cross-domain state changes occur only through declared authority ports and Stage-1 transactions.
4. Domain kernels may read only legal projections exposed by their dependencies.
5. No domain kernel may inspect another kernel's private state.
6. No observer output may write into causal state.
7. No ecological or human outcome may be injected to satisfy a target result.
8. Deterministic seed streams are derived from explicit namespaces.
9. Every committed state change must be represented in replay evidence.
10. A surprising run result is not accepted as reproducible unless checkpoint/replay reproduces it.

## G0 fixture rule

G0 uses Stage-1 `StateAuthority` only as a blank integration fixture owning one resource:

- authority: `genesis.system`
- resource: `tick`

This resource proves that the Genesis runner can advance, persist, restore, and replay through the existing coordination layer.

It is **not** a physical-world kernel and must not accumulate terrain, weather, matter, ecology, human, or observer state.

G1 must introduce explicit physical-world ownership rather than extending the G0 fixture into a universal state bucket.

## Time

Genesis uses the Stage-1 `TemporalOrchestrator`. The clock callback executes once per logical epoch and emits one transaction incrementing the G0 tick marker.

Wall-clock time never controls causality.

## Provenance

The G0 operation label is `GENESIS_CLOCK_TICK`. Every tick produces deterministic proposal and transaction IDs derived from the logical epoch.

## Exit requirement

G0 passes only when a blank Genesis world:

- advances deterministically;
- checkpoints at a clean boundary;
- restores with the same configuration;
- continues to the same final state and ledger digest as an uninterrupted run;
- rejects restore under a mismatched configuration.
