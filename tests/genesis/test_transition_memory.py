"""Write-only transition memory: full-world parity and exact checkpoint replay."""

from copy import deepcopy
from dataclasses import replace

import pytest

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import transitions as tm
from qualification.genesis.tier_observer import build_config


def strip_memory(state):
    state = deepcopy(state)
    state.pop('transition_model', None)
    for person in state['humans']:
        person.get('cognition', {}).pop('transition_memory', None)
    return state


@pytest.mark.parametrize('seed', ['agentus-demography-a', 'agentus-demography-b', 'agentus-g10-4-01'])
def test_recording_preserves_all_existing_state_for_75_days(seed):
    off_config = build_config(seed, 'v1')
    off = GenesisSimulation(off_config)
    on = GenesisSimulation(replace(off_config, agentus_transition_model=tm.MODEL))
    for day in range(75):
        off.run(1)
        on.run(1)
        assert strip_memory(on.human_state()) == off.human_state(), day
        assert on.world_state() == off.world_state(), day
        assert on.ecology_state() == off.ecology_state(), day
        assert on.matter_state() == off.matter_state(), day
        assert on.consumer_state() == off.consumer_state(), day
    people = on.human_state()['humans']
    assert any(p.get('cognition', {}).get('transition_memory', {}).get('edges') for p in people)
    for p in people:
        memory = p.get('cognition', {}).get('transition_memory', {})
        assert len(memory.get('edges', [])) <= tm.MAX_TRANSITIONS
        assert len(memory.get('recent', [])) <= tm.RECENT_LENGTH
    assert on.ledger.verify_chain() and off.ledger.verify_chain()


def test_weather_enabled_memory_survives_checkpoint_with_identical_replay(tmp_path):
    config = replace(build_config('agentus-demography-a', 'v1'),
                     agentus_transition_model=tm.MODEL,
                     genesis_wind_enabled=True, agentus_subcell_position_enabled=True)
    uninterrupted = GenesisSimulation(config)
    uninterrupted.run(40)
    split = GenesisSimulation(config)
    split.run(17)
    path = tmp_path / 'transitions.json'
    split.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, config)
    assert restored.human_state() == split.human_state()
    assert any(p.get('cognition', {}).get('transition_memory', {}).get('edges')
               for p in restored.human_state()['humans'])
    restored.run(23)
    assert restored.snapshot() == uninterrupted.snapshot()
    assert restored.human_state() == uninterrupted.human_state()
    assert restored.ledger.verify_chain()
    with pytest.raises(ValueError, match='fingerprint'):
        GenesisSimulation.load_checkpoint(path, replace(config, agentus_transition_model='none'))
