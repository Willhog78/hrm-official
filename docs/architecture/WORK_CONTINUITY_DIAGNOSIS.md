# Work continuity census

This qualification observer diagnoses the incremental-interlace-v1 / local-material-v1 / experienced-transitions-v4 bundle. It changes no runtime code, configuration, choices, material, reward, or production defaults.

`qualification/genesis/work_continuity.py` wraps the live movement chooser, interaction chooser and physical executor. Each original runs exactly once with its original arguments; the returned result is passed through. Observer records stay outside simulation state and cognition. Hooks are restored in `finally`. Run each world in a separate process when running concurrently; the wrappers are module globals, not thread safe.

The observer registers an actor/cell worksite only after that actor's physical wood action changes the loose or arranged pools. It counts later movement decisions at that cell, departures, returns observed by a later movement decision, and physical work on distinct days. A visit by another actor is not an own return. A failed or unchanged physical action does not register progress. Wood provenance is not tracked: these are own previously worked cells, not exclusively owned material or projects.

Departure stock is explicitly **last observed** during an interaction, not a contemporaneous hidden-state measurement. Weathering and other actors may change stocks between observations. Food/water adequacy is taken from the movement perception and declared needs; it does not identify the causal reason for a move. A return arriving on the final tick, or followed by death before the next movement decision, may go uncounted. Location-memory inspection measures which fields exist, not their influence on planning.

For the three actual interaction keys (force wood, arrange wood, extend surface), report both choice-decision counts and unique actor-day exposure counts. Agent-day labels can overlap: an actor can decline one step and select the same option on another step that day. Untried, positive and nonpositive labels refer to the agent's current learned single-action value, not observer appraisals or full sequence predictions. Reserve readiness uses the existing two-day energy/water checks. Presence of an option does not guarantee a successful physical outcome.

For surfaces, removal and reacquisition count actual ownership/worn-state changes of the same object ID. Only a successful grasp by its remover counts as an own reacquisition; a failed grasp or someone else's grasp does not. Repeated removals can count repeated reacquisitions of one surface; these are events, not unique objects.

The year-long gate compares every fingerprint and ledger digest with the previously captured three untrained PR #48 worlds. It additionally checks chain integrity and element, water and lithic conservation. A focused test compares complete observed/unobserved snapshots, verifies restoration, and exercises departure, return, pool-option and surface ownership semantics. No autonomous useful practice, causation of non-selection, or cultural transmission is inferred from continuity counts.

Reproduce:

```bash
PYTHONPATH=src:. python -m qualification.genesis.work_continuity \
  --output experiments/genesis/summaries/WORK_CONTINUITY_2026-10-10.json
PYTHONPATH=src:. python -m pytest -q -o addopts='' \
  tests/genesis/test_work_continuity.py tests/genesis/test_surface_work_gate.py \
  tests/genesis/test_discovery_census.py
```
