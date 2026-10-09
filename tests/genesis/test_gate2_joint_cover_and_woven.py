"""Joint, read-only checks of arranged cover and worn woven matter.

Risk boundary: no edits to geometry, physiology, planner, sources or deployment.
The material arrangement is an explicit test fixture, not an Agentus invention.
"""
from copy import deepcopy

from hrm_genesis.human.biology import _apply_physiology
from hrm_genesis.human.interactions import insulation_c
from hrm_genesis.matter import objects as matter


PROFILE = {"calibrated": True, "thermal_scale": 1.0, "water_capacity_kg": 42.0}
WORLD = {"temperature": 5.0, "terrain_cover": 0.0, "precipitation": 1.0,
         "solar": 0.0, "wind_speed_m_s": 2.0, "wind_from_deg": 0.0}
ARRANGED = {"arranged_material_elements_kg": {"C": 30.0},
            "arrangement_geometry": {"span_m": 1.5, "height_m": 1.2,
                "surface_area_m2": 2.0, "density": 1.0,
                "integrity": 1.0, "orientation_deg": 0.0}}


def _person(name, offset):
    return {"id": name, "energy": 1000.0, "body_water_kg": 42.0,
            "fatigue": 0.0, "injury": 0.0, "core_temperature_c": 37.0,
            "subcell_offset_m": offset}


def _run(offset, arrangement, worn=False):
    person = _person("agentus", offset)
    objects = []
    if worn:
        # Measured autonomous surface, NOT an idealized 1.8 m2 garment.
        objects = [{"id": "observed-surface", "material": "surface",
                    "holder": "agentus", "worn": True, "area_m2": 0.0001630477,
                    "cohesion": 0.8603248981}]
    moderation = insulation_c({"objects": objects}, person["id"])
    _apply_physiology(person, deepcopy(WORLD), False, PROFILE,
                      deepcopy(arrangement), insulation_c=moderation)
    return person, moderation


def test_shared_cover_protects_each_occupant_without_special_shelter_action():
    # Both occupants stand within one unchanged arrangement footprint.
    first, _ = _run((0.0, 0.0), ARRANGED)
    second, _ = _run((0.1, 0.0), ARRANGED)
    outside, _ = _run((3.0, 0.0), ARRANGED)
    assert first["energy"] > outside["energy"]
    assert second["energy"] > outside["energy"]
    assert first["skin_wetness"] < outside["skin_wetness"]
    assert second["skin_wetness"] < outside["skin_wetness"]
    # A depleted arrangement cannot retain the same protective effect.
    depleted = deepcopy(ARRANGED)
    depleted["arranged_material_elements_kg"]["C"] = 0.0
    gone, _ = _run((0.0, 0.0), depleted)
    assert first["energy"] > gone["energy"]


def test_worn_surface_and_arranged_cover_are_independent_physical_inputs():
    bare, _ = _run((0.0, 0.0), {})
    worn_only, moderation = _run((0.0, 0.0), {}, worn=True)
    covered, _ = _run((0.0, 0.0), ARRANGED)
    both, together = _run((0.0, 0.0), ARRANGED, worn=True)
    assert 0.0 < moderation < 0.01
    assert together == moderation
    # The model should not erase physical cover when the wearer adds material.
    assert both["energy"] >= covered["energy"]
    assert worn_only["energy"] >= bare["energy"]
    assert covered["energy"] > bare["energy"]
    # This is a single-step physiological fixture, not discovery or adoption.


def test_woven_geometry_uses_existing_strand_inventory():
    spec = matter.FIBER_SOURCES["bark"]
    mass = matter.fiber_mass_for("bark", sum(spec["length_m"]) / 2,
                                sum(spec["thickness_mm"]) / 2)
    strands = [matter.make_fiber("bark", {"C": mass}, 0.5, 0.5, f"bark-{i}")
               for i in range(8)]
    before = sum(matter.object_mass(s) for s in strands)
    surface = matter.interlace(strands, "surface")
    assert surface is not None
    assert 0 < surface["area_m2"] < 1.8
    assert abs(matter.object_mass(surface) - before) < 1e-10
    assert abs(matter.object_elements(surface)["C"] - before) < 1e-10
