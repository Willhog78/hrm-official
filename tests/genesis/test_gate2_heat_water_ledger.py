"""Conservation of heat-related physiological water loss."""
from hrm_genesis.human.biology import _account_heat_water_loss, _apply_physiology


def test_weather_heat_water_is_accounted_once():
    human = {"energy": 50000.0, "body_water_kg": 42.0,
             "fatigue": 0.0, "injury": 0.0, "core_temperature_c": 37.0}
    world = {"temperature": 55.0, "wind_speed_m_s": 5.0,
             "precipitation": 0.0, "solar": 1.0}
    profile = {"calibrated": True, "thermal_scale": 1.0,
               "water_capacity_kg": 42.0}
    before = human["body_water_kg"]
    _apply_physiology(human, world, False, profile)
    after = human["body_water_kg"]
    assert 0 < after < before
    matter = {"water_output_kg": 3.0}
    credited = _account_heat_water_loss(matter, world, before, after)
    assert abs(credited - (before - after)) < 1e-12
    assert abs(after + matter["water_output_kg"] - (before + 3.0)) < 1e-12


def test_legacy_accounting_unchanged():
    matter = {"water_output_kg": 3.0}
    assert _account_heat_water_loss(matter, {"temperature": 55.0}, 42.0, 41.0) == 0
    assert matter["water_output_kg"] == 3.0


def test_zero_loss_never_creates_output():
    matter = {"water_output_kg": 0.0}
    assert _account_heat_water_loss(matter, {"wind_speed_m_s": 3.0}, 40.0, 40.0) == 0
    assert _account_heat_water_loss(matter, {"wind_speed_m_s": 3.0}, 40.0, 41.0) == 0
    assert matter["water_output_kg"] == 0.0
