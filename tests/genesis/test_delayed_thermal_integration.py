"""V3 checkpoint and experiment version boundaries."""

from dataclasses import replace

import pytest

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import transitions as tm
from qualification.genesis.tier_observer import build_config


def test_v3_weather_checkpoint_preserves_all_authorities_and_rejects_conversion(tmp_path):
    config = replace(build_config('agentus-demography-a', 'v1-transitionsv3'),
                     genesis_wind_enabled=True, agentus_subcell_position_enabled=True)
    full = GenesisSimulation(config)
    full.run(35)
    split = GenesisSimulation(config)
    split.run(13)
    path = tmp_path / 'delayed-transitions.json'
    split.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, config)
    restored.run(22)
    assert restored.snapshot() == full.snapshot()
    assert restored.human_state() == full.human_state()
    assert restored.ledger.verify_chain()
    for human in restored.human_state()['humans']:
        assert len(human.get('thermal_trials', {})) <= 2
        assert 'arrangement_saving_kcal' not in human
        assert 'insulation_saving_kcal' not in human
    with pytest.raises(ValueError, match='fingerprint'):
        GenesisSimulation.load_checkpoint(path, replace(config, agentus_transition_model=tm.VALUED_MODEL))


def test_v3_is_explicit_and_requires_received_energy_accounting():
    base = build_config('agentus-demography-a', 'v1')
    delayed = build_config('agentus-demography-a', 'v1-transitionsv3')
    assert delayed.agentus_transition_model == tm.DELAYED_MODEL
    assert {**delayed.__dict__, 'agentus_transition_model': 'none'} == base.__dict__
    with pytest.raises(ValueError, match='energy accounting'):
        replace(delayed, child_energy_store='legacy-unscaled')
