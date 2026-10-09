"""Isolated thermal exposure challenge: fixed food/water, no scripted actions."""
from copy import deepcopy
from hrm_genesis.human.biology import _apply_physiology

PROFILE = {"calibrated": True, "thermal_scale": 1.0, "water_capacity_kg": 42.0}
BASE = {"energy": 100000.0, "body_water_kg": 42.0, "fatigue": 0.0,
        "injury": 0.0, "core_temperature_c": 37.0}
COVER = {"arranged_material_elements_kg": {"C": 30.0},
         "arrangement_geometry": {"span_m": 1.5, "height_m": 1.2,
             "surface_area_m2": 2.0, "density": 1.0, "integrity": 1.0,
             "orientation_deg": 0.0}}

def challenge(label, temperature, rain, wind, cover=False, insulation=0.0, position=(0., 0.)):
    person = deepcopy(BASE)
    person["subcell_offset_m"] = position
    world = {"temperature": temperature, "precipitation": rain, "solar": 0.5,
             "wind_speed_m_s": wind, "wind_from_deg": 0.0, "terrain_cover": 0.0}
    pcell = deepcopy(COVER) if cover else {}
    water_loss = 0.0
    for day in range(1, 61):
        prior = person["body_water_kg"]
        _apply_physiology(person, world, False, PROFILE, pcell, insulation_c=insulation)
        water_loss += prior - person["body_water_kg"]
        # Keep water constant for the next tick to isolate thermal damage.
        person["body_water_kg"] = 42.0
    print(f"THERMAL arm={label} injury={person['injury']:.6f} cold={person.get('cold_exposure',0):.6f} "
          f"heat={person.get('heat_exposure',0):.6f} energy_used={BASE['energy']-person['energy']:.6f} "
          f"thermal_water_loss={water_loss:.6f}", flush=True)
    return person

def main():
    cold_bare = challenge("cold_bare", -15.0, 3.0, 8.0)
    cold_insulated = challenge("cold_insulated", -15.0, 3.0, 8.0, insulation=12.0)
    hot_bare = challenge("hot_bare", 55.0, 0.0, 3.0)
    hot_shaded = challenge("hot_shaded", 55.0, 0.0, 3.0, cover=True)
    hot_outside = challenge("hot_outside", 55.0, 0.0, 3.0, cover=True, position=(4.,0.))
    assert cold_insulated["cold_exposure"] < cold_bare["cold_exposure"], "insulation fails to reduce cold stress"
    assert hot_shaded["heat_exposure"] < hot_outside["heat_exposure"], "cover fails to reduce hot stress at incident position"
    assert hot_shaded["heat_exposure"] < hot_bare["heat_exposure"], "cover fails against bare hot exposure"
    print("THERMAL_CHALLENGE_COMPLETE", flush=True)

if __name__ == "__main__":
    main()
