import math
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.world.climate import wind_vector_m_s


def test_wind_is_deterministic_and_spatially_coherent():
    a = wind_vector_m_s(seed="wind-case", epoch=7, ticks_per_year=365, x=0, y=0)
    assert a == wind_vector_m_s(seed="wind-case", epoch=7, ticks_per_year=365, x=0, y=0)
    assert a == wind_vector_m_s(seed="wind-case", epoch=7, ticks_per_year=365, x=1, y=1)
    assert all(math.isfinite(v) and abs(v) <= 5 for v in a)


def test_wind_opt_in_preserves_old_world_and_config_fingerprint():
    base = GenesisConfig(master_seed="wind-legacy")
    enabled = GenesisConfig(master_seed="wind-legacy", genesis_wind_enabled=True)
    assert base.fingerprint() != enabled.fingerprint()
    old_world = GenesisSimulation(base).world_state()
    wind_world = GenesisSimulation(enabled).world_state()
    assert "wind_model" not in old_world
    assert not any("wind_speed_m_s" in c for c in old_world["cells"])
    assert wind_world["wind_model"] == "persistent-vector-v1"
    sim = GenesisSimulation(enabled)
    sim.run(2)
    for c in sim.world_state()["cells"]:
        assert math.isclose(c["wind_speed_m_s"], math.hypot(c["wind_east_m_s"], c["wind_north_m_s"]), abs_tol=1e-8)
        assert 0 <= c["wind_from_deg"] < 360
