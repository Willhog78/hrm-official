"""Explicit V4 mode, bounded checkpoint state and exact replay."""

from dataclasses import replace

import pytest

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import transitions as tm
from qualification.genesis.tier_observer import build_config


def test_procedural_weather_checkpoint_replays_every_authority_exactly(tmp_path):
    config = replace(build_config('agentus-demography-a', 'v1-transitionsv4'),
                     genesis_wind_enabled=True, agentus_subcell_position_enabled=True)
    full = GenesisSimulation(config)
    full.run(35)
    split = GenesisSimulation(config)
    split.run(13)
    path = tmp_path / 'procedural.json'
    split.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, config)
    restored.run(22)
    assert restored.snapshot() == full.snapshot()
    assert restored.human_state() == full.human_state()
    assert restored.ledger.verify_chain()
    for human in restored.human_state()['humans']:
        memory = human.get('cognition', {}).get('transition_memory', {})
        assert len(memory.get('links', [])) <= tm.MAX_LINKS
        assert len(memory.get('edges', [])) <= tm.MAX_TRANSITIONS
        assert len(human.get('thermal_trials', {})) <= 2
        assert 'arrangement_saving_kcal' not in human
    with pytest.raises(ValueError, match='fingerprint'):
        GenesisSimulation.load_checkpoint(path, replace(config, agentus_transition_model=tm.DELAYED_MODEL))


def test_v4_is_explicit_and_old_modes_remain_available():
    base = build_config('agentus-demography-a', 'v1')
    procedural = build_config('agentus-demography-a', 'v1-transitionsv4')
    assert procedural.agentus_transition_model == tm.PROCEDURAL_MODEL
    assert {**procedural.__dict__, 'agentus_transition_model': 'none'} == base.__dict__
    assert build_config('agentus-demography-a', 'v1-transitionsv3').agentus_transition_model == tm.DELAYED_MODEL
    with pytest.raises(ValueError, match='energy accounting'):
        replace(procedural, child_energy_store='legacy-unscaled')
