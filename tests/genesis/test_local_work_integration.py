"""Version isolation and full transactional checkpoint/replay for local work."""

from dataclasses import replace

import pytest

from hrm_genesis import GenesisSimulation
from qualification.genesis.discovery import Census
from qualification.genesis.tier_observer import build_config, conservation_errors


def config():
    return replace(build_config('agentus-demography-a', 'v1-transitionsv4'),
                   genesis_wind_enabled=True, agentus_subcell_position_enabled=True,
                   agentus_local_work_enabled=True)


def test_local_work_is_explicit_and_rejects_missing_positions():
    active = config()
    legacy = replace(active, agentus_local_work_enabled=False)
    assert active.fingerprint() != legacy.fingerprint()
    assert 'local_work_model' not in GenesisSimulation(legacy).human_state()
    assert GenesisSimulation(active).human_state()['local_work_model'] == 'local-material-v1'
    with pytest.raises(ValueError, match='local work requires'):
        replace(active, agentus_subcell_position_enabled=False)


def test_full_local_work_replays_and_observation_remains_invisible(tmp_path):
    active = config()
    full = GenesisSimulation(active)
    census = Census(thermal_exposure=True)
    census.install()
    try:
        for day in range(1, 36):
            census.day = day
            full.run(1)
    finally:
        census.uninstall()
    split = GenesisSimulation(active)
    split.run(13)
    path = tmp_path / 'local-work.json'
    split.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, active)
    restored.run(22)
    assert restored.snapshot() == full.snapshot()
    assert restored.human_state() == full.human_state()
    assert restored.ledger.digest() == full.ledger.digest()
    assert full.ledger.verify_chain()
    assert max(census._per_tick.values(), default=0) <= 3
    assert any(k.startswith('move:local_') for k in census.attempts)
    assert max(abs(v) for v in conservation_errors(full).values()) < 1e-9
    with pytest.raises(ValueError, match='fingerprint'):
        GenesisSimulation.load_checkpoint(path, replace(active, agentus_local_work_enabled=False))
