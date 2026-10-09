"""Quantify the physical scale of observed autonomous woven-surface protection.

Observation-only qualification. No changes to Agentus choices, physiology,
world state, or reward. The observed surface area comes from the 365-day
production-profile audit; other scenarios are explicitly counterfactual.
"""
from copy import deepcopy
from math import ceil

from hrm_genesis.human import interactions as cap
from hrm_genesis.human.biology import _apply_physiology

OBSERVED_AREA_M2 = 0.0001630477  # first retained surface, seed a, day 110
OBSERVED_COHESION = 0.8603248981
PROFILE = {"calibrated": True, "thermal_scale": 1.0, "water_capacity_kg": 42.0}
WORLD = {"temperature": -15.0, "precipitation": 3.0, "solar": 0.5,
         "wind_speed_m_s": 8.0, "wind_from_deg": 0.0, "terrain_cover": 0.0}


def trial(count):
    person = {"id": "h", "energy": 10000.0, "body_water_kg": 42.0,
              "fatigue": 0.0, "injury": 0.0, "core_temperature_c": 37.0}
    surfaces = [{"id": f"surface-{i}", "material": "surface",
                 "holder": "h", "worn": True, "area_m2": OBSERVED_AREA_M2,
                 "cohesion": OBSERVED_COHESION} for i in range(count)]
    # All surfaces are worn in this hypothetical challenge; no claim that
    # Agentus has actually assembled or worn this many.
    moderation = cap.insulation_c({"objects": surfaces}, "h")
    _apply_physiology(person, deepcopy(WORLD), False, PROFILE, {},
                      insulation_c=moderation)
    return moderation, person


def main():
    bare_c, bare = trial(0)
    one_c, one = trial(1)
    assert bare_c == 0
    assert 0 < one_c < 0.01, "one tiny observed surface has overstated insulation"
    assert one["energy"] >= bare["energy"]

    # Compute necessary quantity from actual area/cohesion and model constants;
    # do not insert a fictional large garment into the autonomous audit.
    equivalent_count = ceil(cap.BODY_SURFACE_M2 /
                           (OBSERVED_AREA_M2 * OBSERVED_COHESION))
    for count in (1, 7, 100, equivalent_count):
        moderation, person = trial(count)
        print(f"SURFACE_SCALE hypothetical_count={count} "
              f"coverage_m2={count * OBSERVED_AREA_M2 * OBSERVED_COHESION:.8f} "
              f"insulation_c={moderation:.8f} "
              f"thermal_saving_kcal={person.get('insulation_saving_kcal', 0):.8f}",
              flush=True)
    print(f"SURFACE_SCALE observed_single_area_m2={OBSERVED_AREA_M2} "
          f"observed_single_cohesion={OBSERVED_COHESION} "
          f"theoretical_count_for_full_body_coverage={equivalent_count}", flush=True)
    print("SURFACE_SCALE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
