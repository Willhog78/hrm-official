from copy import deepcopy
from hrm_genesis.human.biology import _apply_physiology


def test_live_thermal_cost_depends_on_position_and_wind():
    profile = {"calibrated": True, "thermal_scale": 1.0,
               "water_capacity_kg": 42.0}
    arrangement = {"arranged_material_elements_kg": {"C": 30.0},
                   "arrangement_geometry": {"span_m": 1.5, "height_m": 1.2,
                   "surface_area_m2": 2.0, "density": 1.0,
                   "integrity": 1.0, "orientation_deg": 0.0}}
    world = {"temperature": 50.0, "terrain_cover": 0.0,
             "wind_speed_m_s": 6.0, "wind_from_deg": 0.0}
    base = {"energy": 1000.0, "body_water_kg": 42.0,
            "fatigue": 0.0, "injury": 0.0, "core_temperature_c": 37.0}
    centre = deepcopy(base)
    away = deepcopy(base)
    reverse = deepcopy(base)
    away["subcell_offset_m"] = (4.0, 0.0)
    _apply_physiology(centre, world, False, profile, arrangement)
    _apply_physiology(away, world, False, profile, arrangement)
    against = dict(world, wind_from_deg=180.0)
    _apply_physiology(reverse, against, False, profile, arrangement)
    assert centre["energy"] > away["energy"]
    assert centre["energy"] > reverse["energy"]


def test_windless_legacy_defaults_do_not_need_new_state():
    p = {"calibrated": True, "thermal_scale": 1.0, "water_capacity_kg": 42.0}
    h = {"energy": 1000., "body_water_kg": 42., "fatigue": 0., "injury": 0.,
         "core_temperature_c": 37.}
    _apply_physiology(h, {"temperature": 20.0}, False, p)
    assert h["energy"] == 1000.
