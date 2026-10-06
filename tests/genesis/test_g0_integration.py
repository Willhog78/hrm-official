from __future__ import annotations

from pathlib import Path

import pytest

from hrm_genesis import GenesisConfig, GenesisSimulation


def canonical_snapshot(sim: GenesisSimulation):
    snap = sim.snapshot()
    return snap.epoch, snap.ledger_digest, snap.authorities


def test_blank_world_advances_deterministically():
    config = GenesisConfig(master_seed="g0-determinism", physical_world_enabled=False, matter_enabled=False)

    a = GenesisSimulation(config)
    b = GenesisSimulation(config)

    a.run(32)
    b.run(32)

    assert canonical_snapshot(a) == canonical_snapshot(b)
    assert a.snapshot().authorities["genesis.system"]["tick"]["value"] == 32
    assert a.ledger.verify_chain()


def test_checkpoint_restore_matches_uninterrupted_run(tmp_path: Path):
    config = GenesisConfig(master_seed="g0-checkpoint", physical_world_enabled=False, matter_enabled=False)

    uninterrupted = GenesisSimulation(config)
    uninterrupted.run(40)

    split = GenesisSimulation(config)
    split.run(13)
    checkpoint = tmp_path / "g0.json"
    split.write_checkpoint(checkpoint)

    restored = GenesisSimulation.load_checkpoint(checkpoint, config)
    restored.run(27)

    assert canonical_snapshot(restored) == canonical_snapshot(uninterrupted)
    assert restored.ledger.verify_chain()


def test_restore_rejects_config_mismatch(tmp_path: Path):
    original = GenesisConfig(master_seed="g0-original", physical_world_enabled=False, matter_enabled=False)
    sim = GenesisSimulation(original)
    sim.run(2)
    checkpoint = tmp_path / "g0.json"
    sim.write_checkpoint(checkpoint)

    with pytest.raises(ValueError, match="fingerprint"):
        GenesisSimulation.load_checkpoint(
            checkpoint,
            GenesisConfig(master_seed="different", physical_world_enabled=False, matter_enabled=False),
        )


def test_seed_namespaces_are_isolated():
    config = GenesisConfig(master_seed="g0-seeds", physical_world_enabled=False, matter_enabled=False)
    sim = GenesisSimulation(config)

    first = sim.seed_bank.stream("world.weather")
    expected = [first.random() for _ in range(4)]

    unrelated = sim.seed_bank.stream("ecology.future")
    for _ in range(100):
        unrelated.random()

    repeated = sim.seed_bank.stream("world.weather")
    assert [repeated.random() for _ in range(4)] == expected
