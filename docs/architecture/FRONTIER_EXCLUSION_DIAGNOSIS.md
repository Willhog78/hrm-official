# Live frontier exclusion diagnosis

This read-only qualification observes the unchanged V4 + procedural-frontier-v1 + local-work + incremental-surface bundle. No runtime file, choice rule, material, cost, reward, production setting or agent memory changes.

`qualification/genesis/frontier_exclusions.py` wraps the live chooser once. It observes the chooser's actual `sequence-frontier` draw through a temporary context-instance proxy that calls the original draw exactly once and returns the exact result. The prior instance override is restored, or the temporary attribute is removed so the original class method is inherited again, including on exceptions. The original chooser result is returned unchanged. The global chooser hook is restored in `finally`. Concurrent worlds run in separate processes; module-global wrappers are not thread safe.

After choice, diagnostic predicates inspect the actor's unchanged current action values and retained physical experiences. Inspection uses the same V4 projection and existing eight/16 attempt limits as the active chooser. It does not invoke the chooser again, draw another random value, alter a before/after record, apply a predicted outcome, or expose observer records to Agentus.

Each offered **option entry per choice call** receives exactly one label, in this order:

1. `untried_single_action`: not yet known to single-action learning; eligible for ordinary novelty, but not for the known-action frontier.
2. `reserve_blocked`: the existing two-basal/two-water discretionary guard fails.
3. `preempted:*`: the actual earlier valued-plan, imitation or ordinary-novelty choice returned before reaching the frontier.
4. `no_retained_attempt`: no own retained transition for this action. This does not distinguish never experiencing it from forgetting/eviction.
5. `physical_state_mismatch`: retained own attempts exist, but no matching before-state at the current perceptual resolution.
6. `no_enabled_successor`: a matching own attempt exists but none of its outcomes enabled another action.
7. `attempt_budget_exhausted`: enabling experience exists, but all matching outcomes sum to at least the current eight/16 limit.
8. Candidate result: actual trial draw declined, this key selected, or another frontier key selected.

Calls and option-entry counts are separate denominators. Duplicate entries with one key can share a selected-key label; `actual_frontier_selections` counts the real choice call once. Options skipped by an earlier choice are not counted as hypothetical physical mismatches. Empty option lists do not reach the frontier. An eligible list without an actual draw, or a draw without eligible options, is a diagnostic consistency error and fails the gate.

For physical mismatches, the observer reports differing top-level fields of the closest retained **same-action** before-state, using the fewest differing physical fields and stable edge ID for ties. Ordinary energy/water/fatigue drift is excluded; injury remains. These are local perceptual discrepancies, not causal prerequisites or justification for ignoring a field. Whole `pools`, `weather`, `held`, `ground`, `geometry`, `acts` etc. fields can each contain several subfeatures. Counts overlap because one closest state can differ in several fields. No hidden material identity, nutritional utility or another individual's inventory is used to repair the agent's prediction.

Qualification compares the three 365-day config fingerprints and ledger hashes with PR #50's captured active worlds, and checks chain integrity, conservation and diagnostic consistency. A focused test also compares complete 20-day observed/unobserved snapshots. Synthetic tests exercise the actual live chooser's exclusion cases and verify draw restoration; they are correctness fixtures, not ecological discovery claims.

```bash
PYTHONPATH=src:. python -m qualification.genesis.frontier_exclusions \
  --output experiments/genesis/summaries/FRONTIER_EXCLUSIONS_2026-10-10.json
PYTHONPATH=src:. python -m pytest -q -o addopts='' \
  tests/genesis/test_frontier_exclusions.py \
  tests/genesis/micro/test_micro_frontier_state.py \
  tests/genesis/test_frontier_state_integration.py \
  tests/genesis/test_discovery_census.py
```
