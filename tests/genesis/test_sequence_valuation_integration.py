"""V2 replay, observer isolation and independent calibration safeguards."""

from dataclasses import replace

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import transitions as tm
from qualification.genesis.tier_observer import build_config


def test_v2_weather_checkpoint_replays_exactly(tmp_path):
    config = replace(build_config('agentus-demography-a', 'v1-transitionsv2'),
                     genesis_wind_enabled=True, agentus_subcell_position_enabled=True)
    full = GenesisSimulation(config)
    full.run(35)
    split = GenesisSimulation(config)
    split.run(13)
    path = tmp_path / 'valued-transitions.json'
    split.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, config)
    assert restored.human_state() == split.human_state()
    restored.run(22)
    assert restored.snapshot() == full.snapshot()
    assert restored.human_state() == full.human_state()
    assert restored.ledger.verify_chain()
    state = restored.human_state()
    for p in state['humans']:
        assert 'arrangement_saving_kcal' not in p
        memory = p.get('cognition', {}).get('transition_memory', {})
        assert len(memory.get('edges', [])) <= tm.MAX_TRANSITIONS
        assert len(memory.get('recent', [])) <= tm.RECENT_LENGTH
        if memory:
            assert memory['model'] == tm.VALUED_MODEL


def test_experiment_suffixes_preserve_default_and_old_recording_modes():
    base = build_config('agentus-demography-a', 'v1')
    recorded = build_config('agentus-demography-a', 'v1-transitionsv1')
    valued = build_config('agentus-demography-a', 'v1-transitionsv2')
    assert base.agentus_transition_model == 'none'
    assert recorded.agentus_transition_model == tm.MODEL
    assert valued.agentus_transition_model == tm.VALUED_MODEL
    assert {**recorded.__dict__, 'agentus_transition_model': 'none'} == base.__dict__
    assert {**valued.__dict__, 'agentus_transition_model': 'none'} == base.__dict__
