"""New recognition version is explicit; full physical replay stays exact."""

from dataclasses import replace

import pytest

from hrm_genesis import GenesisSimulation
from qualification.genesis.discovery import Census, config_for


def config(active=True):
    return replace(config_for('agentus-demography-a', True), agentus_local_work_enabled=True,
                   agentus_surface_work_enabled=True, agentus_frontier_state_enabled=active)


def test_frontier_version_is_opt_in_and_requires_v4():
    old = config(False)
    active = config()
    assert active.fingerprint() != old.fingerprint()
    assert 'frontier_state_model' not in GenesisSimulation(old).human_state()
    assert GenesisSimulation(active).human_state()['frontier_state_model'] == 'procedural-frontier-v1'
    for model in ('none', 'experienced-transitions-v1', 'experienced-transitions-v2', 'experienced-transitions-v3'):
        with pytest.raises(ValueError, match='frontier state recognition requires'):
            replace(active, agentus_transition_model=model)


def test_recognition_checkpoint_observation_and_physical_limits(tmp_path):
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
    path = tmp_path / 'frontier.json'
    split.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, active)
    restored.run(22)
    assert full.snapshot() == restored.snapshot()
    assert full.ledger.digest() == restored.ledger.digest()
    assert full.ledger.verify_chain()
    assert max(census._per_tick.values(), default=0) <= 3
    with pytest.raises(ValueError, match='fingerprint'):
        GenesisSimulation.load_checkpoint(path, config(False))
