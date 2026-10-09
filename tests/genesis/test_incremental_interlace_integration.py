"""Opt-in isolation, bounded observation, and checkpoint replay."""

from dataclasses import replace

import pytest

from hrm_genesis import GenesisSimulation
from qualification.genesis.discovery import Census
from qualification.genesis.tier_observer import build_config, conservation_errors


def config():
    return replace(build_config('agentus-demography-a', 'v1-transitionsv4'),
                   genesis_wind_enabled=True, agentus_subcell_position_enabled=True,
                   agentus_local_work_enabled=True, agentus_surface_work_enabled=True)


def test_incremental_version_is_explicit():
    active = config()
    old = replace(active, agentus_surface_work_enabled=False)
    assert active.fingerprint() != old.fingerprint()
    assert 'surface_work_model' not in GenesisSimulation(old).human_state()
    assert GenesisSimulation(active).human_state()['surface_work_model'] == 'incremental-interlace-v1'
    with pytest.raises(ValueError, match='surface work requires'):
        replace(build_config('agentus-demography-a', 'v1'), agentus_capacities_enabled=False,
                agentus_surface_work_enabled=True)


def test_opt_in_world_matches_unobserved_checkpoint_replay(tmp_path):
    active = config()
    full = GenesisSimulation(active)
    observer = Census(thermal_exposure=True)
    observer.install()
    try:
        for day in range(1, 36):
            observer.day = day
            full.run(1)
    finally:
        observer.uninstall()
    split = GenesisSimulation(active)
    split.run(13)
    path = tmp_path / 'incremental.json'
    split.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, active)
    restored.run(22)
    assert restored.snapshot() == full.snapshot()
    assert restored.ledger.digest() == full.ledger.digest()
    assert restored.ledger.verify_chain()
    assert max(observer._per_tick.values(), default=0) <= 3
    assert max(abs(v) for v in conservation_errors(full).values()) < 1e-9
    with pytest.raises(ValueError, match='fingerprint'):
        GenesisSimulation.load_checkpoint(path, replace(active, agentus_surface_work_enabled=False))
