"""Gate 2 cumulative wet/cold/heat outcomes; legacy physiology untouched."""
from hrm_genesis.human.biology import _apply_physiology


PROFILE = {"calibrated": True, "thermal_scale": 1.0, "water_capacity_kg": 42.0}


def agent():
    return {"energy": 50000.0, "body_water_kg": 42.0,
            "fatigue": 0.0, "injury": 0.0, "core_temperature_c": 37.0}


def step(h, temp, rain=0.0, wind=0.0, solar=0.0):
    _apply_physiology(h, {"temperature": temp, "precipitation": rain,
        "wind_speed_m_s": wind, "solar": solar}, False, PROFILE)


def test_persistent_wetness_drives_wind_chill_and_gradual_drying():
    wet, dry = agent(), agent()
    step(wet, -5.0, rain=4.0, wind=10.0)
    step(dry, -5.0, rain=0.0, wind=10.0)
    assert wet["skin_wetness"] == 1.0
    assert wet["energy"] < dry["energy"]
    previous = wet["skin_wetness"]
    step(wet, 20.0, wind=10.0, solar=1.0)
    assert 0.0 < wet["skin_wetness"] < previous


def test_repeated_cold_is_worse_and_warmth_allows_recovery():
    h = agent()
    for _ in range(35):
        step(h, -12.0, rain=4.0, wind=10.0)
    assert h["cold_exposure"] > 6.0
    assert h["injury"] > 0.0
    prior = h["cold_exposure"]
    for _ in range(15):
        step(h, 22.0, solar=1.0)
    assert h["cold_exposure"] < prior


def test_heat_stress_accumulates_then_dissipates():
    h = agent()
    for _ in range(35):
        step(h, 56.0)
    assert h["heat_exposure"] > 6.0
    assert h["injury"] > 0.0
    before = h["heat_exposure"]
    for _ in range(15):
        step(h, 22.0)
    assert h["heat_exposure"] < before


def test_windless_historical_state_unmodified():
    h = agent()
    for _ in range(3):
        _apply_physiology(h, {"temperature": -5.0}, False, PROFILE)
    assert "skin_wetness" not in h
    assert "cold_exposure" not in h
    assert "heat_exposure" not in h
