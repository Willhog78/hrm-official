from hrm_genesis.human.actions import execute_live_sequence
from hrm_genesis.human.biology import _structural_protection


def cell(mass):
    return {"woody_elements_kg": {"C": 0.0}, "loose_material_elements_kg": {"C": mass}, "arranged_material_elements_kg": {"C": 0.0}, "arrangement_geometry": {"span_m": 0.0, "height_m": 0.0, "surface_area_m2": 0.0, "density": 0.0}}


def test_mass_constrains_geometry_and_removal():
    _, small, _ = execute_live_sequence(("arrange",), {}, cell(.001))
    _, big, _ = execute_live_sequence(("arrange",), {}, cell(5.0))
    assert small["arrangement_geometry"]["surface_area_m2"] < big["arrangement_geometry"]["surface_area_m2"]
    assert small["arrangement_geometry"]["surface_area_m2"] <= .001 / 15 + 1e-10
    _, damaged, _ = execute_live_sequence(("separate",), {}, big)
    assert damaged["arrangement_geometry"]["surface_area_m2"] < big["arrangement_geometry"]["surface_area_m2"]
    for c in (small, big, damaged):
        assert abs(sum(c[k]["C"] for k in ("woody_elements_kg", "loose_material_elements_kg", "arranged_material_elements_kg")) - (0.001 if c is small else 5.0)) < 1e-9


def test_protection_checks_surviving_material_even_with_stale_geometry():
    geo = {"span_m": 2.5, "height_m": 2.2, "surface_area_m2": 8.0, "density": 1.0}
    def cover(m):
        return _structural_protection({"terrain_cover": 0.0}, {"arranged_material_elements_kg": {"C": m}, "arrangement_geometry": geo})[1]
    assert cover(0) == 0
    assert 0 < cover(.1) < cover(10)
