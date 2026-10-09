"""Woven surfaces retain their real strand mass during weathering."""
from copy import deepcopy
from hrm_genesis.matter import objects as mo
from hrm_genesis.human.interactions import weather_objects


def test_interlaced_surface_mass_survives_weathering():
    strand = {"material": "fiber", "elements_kg": {"C": 0.02}, "integrity": 1.0}
    surface = {"id": "woven", "material": "surface", "strands": [deepcopy(strand) for _ in range(4)],
               "area_m2": 0.5, "cohesion": 0.8, "x": 0, "y": 0,
               "holder": "human-g00000000", "worn": True}
    assert abs(mo.object_mass(surface) - 0.08) < 1e-12
    state = {"objects": [surface]}
    pcells = {(0, 0): {"fire_intensity": 0.0, "detritus_elements_kg": {"C": 0.0}}}
    wcells = {(0, 0): {"wind_speed_m_s": 1.0, "precipitation": 0.0, "solar": 0.0}}
    before = mo.object_mass(surface) + pcells[(0,0)]["detritus_elements_kg"]["C"]
    weather_objects(state, pcells, wcells, 1)
    assert len(state["objects"]) == 1
    assert state["objects"][0]["worn"] is True
    after = mo.object_mass(state["objects"][0]) + pcells[(0,0)]["detritus_elements_kg"]["C"]
    assert abs(before - after) < 1e-10
