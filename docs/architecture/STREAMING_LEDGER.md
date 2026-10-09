# Streaming replay ledger (2026-10-09)

## Why

`ReplayLedger` kept every epoch's records in RAM. Each Genesis day commits the full state of each authority (`CommittedMutation.new_value`), so a daily world grew by about 0.83 GB per simulated year per seed. A 25-year run would need about 20 GB, while the runner has 8 GB.

The owner chose a leaner ledger over more memory.

## What reads ledger history (inspected before the change)

| Reader | Uses history? |
|---|---|
| Simulation step (`TransactionFabric.resolve`) | No. It uses the last block digest, the next admissible epoch, and the id sets (record, transaction and committed ids) to validate a new batch. |
| `GenesisSimulation.snapshot` | Digest only. |
| Agentus cognition | No. Its memories live in the human authority's current state. |
| Random draws | No. The seed bank seeds only the initial world; daily draws are hashes of (seed, epoch, id). Current state plus epoch fully determine the future. |
| Checkpoint write / load | Yes: `export()` embedded the whole ledger, and `load` replayed it to check the stored state. |
| `verify_chain`, `replay_state`, `fallible_projection` | Yes. These are verification and diagnostic tools, not the simulation. |

So the simulation's outcomes cannot depend on whether history is held in memory.

## Design: `hrm_coordination.StreamingReplayLedger`

- **Same evidence.** Records and epoch blocks are built and digested by the unchanged `ReplayLedger.prepare_batch`, so the digest chain is identical.
- **Streamed to disk.** Each committed epoch is appended to the ledger file as one gzip member holding `{"epoch", "block", "records"}`; the genesis is the first member. Writes are flushed per epoch.
- **Bounded RAM.** Only the last `buffer_epochs` epochs (default 8) stay in memory, plus the id sets admission needs (small strings, a few per day).
- **Checkpoints.** `write_checkpoint` stores the ledger's tip instead of the whole ledger: the file offset, the last block and the offset of its member, the id sets, and, for each resource, the offset of the epoch that last wrote it.
- **Resume.** `load_checkpoint` (and `load_genesis_checkpoint`):
  1. truncates the stream to the tip, discarding any epochs written after the checkpoint;
  2. checks the tail member against the tip digest;
  3. checks the stored authority state against each resource's last committed value, read from the members that wrote them, with each of those members' record and block digests rechecked.

  An edited checkpoint state is rejected, as before.
- **Full verification.** `verify_chain()` streams the whole file with bounded memory and applies the same checks as `ReplayLedger.verify_chain`. `replay_state()` also streams, keeping one value per resource. A tampered stream fails verification (test).
- **Grouping.** `group_epochs` epochs share one compressed member (`codec` "gzip" or "xz"), so day-to-day similarity compresses. A checkpoint flushes the open block first, and locations are recorded as (member offset, epoch).
- **Opt-in.** `GenesisSimulation(config, ledger_path=...)`. Without a path the in-memory ledger is used, exactly as before. The world configuration and fingerprint are unaffected.
- **Note for long runs.** `GenesisSimulation.run(n)` returns all *n* step results; this is the orchestrator's existing interface. Long runners should call `run(1)` per day, as `experiments/genesis/run_generations.py` does, or those results accumulate in memory for the duration of the call.

## Verification

| Check | Result |
|---|---|
| 60 days, seed a | In-memory and streaming digests identical; `verify_chain` passes; `replay_state` identical; checkpoint at day 30 + resume equals uninterrupted (5 days written after the checkpoint were discarded). |
| 5 years, seed a, current default | In-memory, streaming, and checkpoint at 2.5 years + resume give the same ledger digest (`4a55cddd…`), the same world-state digest (`aadb64c3…`) and the same outcomes (15 alive, 7 born, 0 deaths, 3 browsers). |
| 5 years, seed a, `v1-legacystore` (the third run's configuration), streaming runner | Reproduces the third run year by year: alive 12/13/14/15/16; births 4, 1, 1, 1, 1; the same animal deaths and causes; edible plants 47.8, 566.5, 698.6, 768.5 and 771.3 t. |
| Memory | Peak 0.06 GB with the streaming runner, against 4.35 GB with the in-memory ledger. |
| Disk | About 43 MB of ledger per simulated year per seed with per-epoch gzip, or about 21–27 MB with xz in 30-epoch blocks (`group_epochs=30, codec="xz"`, the long-run default). Checkpoints are 1–3 MB. |
| Grouped xz | Same digest as gzip (year 1, seed a: `42ab93ea…`). A checkpoint taken mid-block resumes exactly (test). |
| Tests | `tests/genesis/test_streaming_ledger.py`: identical digest and buffer bound; tamper detection; resume equals uninterrupted, including Agentus state; an edited checkpoint is rejected. |
