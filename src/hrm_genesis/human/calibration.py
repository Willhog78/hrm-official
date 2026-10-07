from __future__ import annotations


def qualification_profile() -> dict[str, float | int | bool]:
    return {
        "calibrated": False,
        "seed_dry_mass_kg": 0.08,
        "water_capacity_kg": 0.85,
        "water_loss_per_tick_kg": 0.06,
        "bite_cap_kg": 0.018,
        "assimilation": 0.72,
        "food_energy_kcal_per_kg": 2200.0,
        "basal_energy_kcal_per_tick": 0.42,
        "move_energy_kcal_per_tick": 0.18,
        "maturity_ticks": 180,
        "max_age_ticks": 900,
        "reproduction_energy_kcal": 18.0,
        "reproduction_cooldown_ticks": 60,
        "offspring_mass_fraction": 0.12,
        "initial_energy_kcal": 15.0,
        "energy_capacity_kcal": 60.0,
        "min_dry_mass_kg": 0.01,
        "min_water_fraction": 0.0,
        "dependent_age_ticks": 0,
        "independent_feeding_age_ticks": 0,
        "nursing_energy_kcal_per_tick": 0.0,
        "nursing_water_kg_per_tick": 0.0,
        "nursing_dry_mass_kg_per_tick": 0.0,
    }


def reference_adult_profile(ticks_per_year: int) -> dict[str, float | int | bool]:
    if ticks_per_year != 365:
        raise ValueError("reference adult calibration requires 365 ticks_per_year (one tick per day)")
    # A neutral reference organism for systems experiments, not an individual
    # medical model. 70 kg total = 42 kg water + 28 kg tracked dry mass.
    return {
        "calibrated": True,
        "reference_total_mass_kg": 70.0,
        "seed_dry_mass_kg": 28.0,
        "water_capacity_kg": 42.0,
        "water_loss_per_tick_kg": 2.5,
        "bite_cap_kg": 1.35,
        "assimilation": 0.80,
        "food_energy_kcal_per_kg": 2200.0,
        "basal_energy_kcal_per_tick": 2000.0,
        "move_energy_kcal_per_tick": 55.0,
        "maturity_ticks": 18 * ticks_per_year,
        "max_age_ticks": 90 * ticks_per_year,
        "reproduction_energy_kcal": 4000.0,
        "reproduction_cooldown_ticks": ticks_per_year,
        "offspring_mass_fraction": 0.05,
        "initial_energy_kcal": 6000.0,
        "energy_capacity_kcal": 30000.0,
        "min_dry_mass_kg": 14.0,
        "min_water_fraction": 0.50,
        "dependent_age_ticks": 2 * ticks_per_year,
        "independent_feeding_age_ticks": 5 * ticks_per_year,
        "nursing_energy_kcal_per_tick": 350.0,
        "nursing_water_kg_per_tick": 0.65,
        "nursing_dry_mass_kg_per_tick": 0.035,
    }


def reference_adult_profile_v2(ticks_per_year: int) -> dict[str, float | int | bool | str]:
    """Energy-budget realism revision of the reference adult (G10.5).

    Declared reference values (broad human ranges, not an individual model):
    - Energy reserve is body fat: capacity 120,000 kcal (about 15.6 kg at
      7,700 kcal/kg, within adult 15-25% fat of 70 kg). Founders start lean at
      60,000 kcal (about 7.8 kg, about 11%).
    - Below an empty reserve, lean dry tissue is catabolized at 4,000 kcal/kg
      (protein). Death follows at the existing 50% dry-mass floor, so total
      fasting survival is roughly six to eight weeks.
    - Hunger tracks short-term balance: the planner's reserve fraction keeps the
      v1 30,000 kcal reference, so planning is not changed by fat storage.
    - Milk: up to 550 kcal/day at full dependence (about 750 ml/day at
      ~0.7 kcal/ml), costing the mother 1/0.8 of that (synthesis efficiency).
      Output tapers when the mother's own reserve falls below 10%.
    - Child basal energy and water turnover scale with body size^0.75 (Kleiber).
    - The reproduction energy threshold keeps its v1 share of the reserve
      (4,000/30,000), i.e. 16,000 kcal.
    """
    profile = dict(reference_adult_profile(ticks_per_year))
    profile.update({
        "physiology_version": "reference-v2",
        "energy_capacity_kcal": 120000.0,
        "initial_energy_kcal": 60000.0,
        "satiety_reference_kcal": 30000.0,
        "lean_catabolism_kcal_per_kg": 4000.0,
        "nursing_energy_kcal_per_tick": 550.0,
        "lactation_efficiency": 0.8,
        "lactation_taper_reserve_fraction": 0.1,
        "metabolic_scaling_exponent": 0.75,
        "reproduction_energy_kcal": 16000.0,
    })
    return profile


PHYSIOLOGY_VERSIONS = ("reference-v1", "reference-v2")


def physiology_profile(*, calibrated: bool, ticks_per_year: int, version: str = "reference-v1") -> dict[str, float | int | bool]:
    if calibrated:
        if version == "reference-v2":
            return reference_adult_profile_v2(ticks_per_year)
        return reference_adult_profile(ticks_per_year)
    return qualification_profile()
