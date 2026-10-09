from copy import deepcopy
from hrm_genesis.human.biology import _structural_protection


def test_arrangement_geometry_position_orientation_integrity_and_mass():
    world = {"terrain_cover": 0.0}
    base = {"arranged_material_elements_kg": {"C": 30.0}, "arrangement_geometry": {
        "span_m": 1.5, "height_m": 1.2, "surface_area_m2": 2.0,
        "density": 1.0, "integrity": 1.0, "orientation_deg": 0.0}}
    def shelter(c, **kwargs):
        return _structural_protection(world, c, **kwargs)[1]
    assert shelter(base, wind_from_deg=0.0) > shelter(base, wind_from_deg=180.0)
    assert shelter(base, occupant_offset_m=(0.0, 0.0)) > shelter(base, occupant_offset_m=(2, 0))
    damaged = deepcopy(base)
    damaged["arrangement_geometry"]["integrity"] = 0.25
    assert 0 < shelter(damaged) < shelter(base)
    burned = deepcopy(base)
    burned["arranged_material_elements_kg"]["C"] = 0.1
    assert 0 < shelter(burned) < shelter(base)
    removed = deepcopy(base)
    removed["arranged_material_elements_kg"]["C"] = 0
    assert shelter(removed) == 0
