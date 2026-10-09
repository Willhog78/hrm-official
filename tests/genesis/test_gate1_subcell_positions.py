from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.biology import _offspring, enable_subcell_positions


def config(**overrides):
    opts = dict(master_seed="subcell-determinism", world_width=4, world_height=4,
                ticks_per_year=365, material_scale_factor=1000.,
                producer_ecology_enabled=True, consumer_ecology_enabled=True,
                human_biology_enabled=True, human_cognition_enabled=True,
                human_actions_enabled=True, human_calibration_enabled=True,
                agentus_capacities_enabled=True)
    opts.update(overrides)
    return GenesisConfig(**opts)


def test_legacy_config_fingerprint_and_state_unchanged():
    assert config().fingerprint() != config(agentus_subcell_position_enabled=True).fingerprint()
    assert not any("subcell_offset_m" in p for p in GenesisSimulation(config()).human_state()["humans"])


def test_opt_in_positions_stable_and_persisted():
    a = GenesisSimulation(config(agentus_subcell_position_enabled=True))
    b = GenesisSimulation(config(agentus_subcell_position_enabled=True))
    assert a.human_state() == b.human_state()
    assert a.human_state()["subcell_position_model"] == "cell-local-v1"
    for human in a.human_state()["humans"]:
        assert all(-0.75 <= value <= 0.75 for value in human["subcell_offset_m"])


def test_newborn_starts_at_caregiver_position():
    from copy import deepcopy
    sim = GenesisSimulation(config(agentus_subcell_position_enabled=True))
    mother = deepcopy(sim.human_state()["humans"][0])
    child = _offspring(mother, 23, sim.human_state()["physiology_profile"])
    assert child["subcell_offset_m"] == mother["subcell_offset_m"]
