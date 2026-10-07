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
    }


def physiology_profile(*, calibrated: bool, ticks_per_year: int) -> dict[str, float | int | bool]:
    if calibrated:
        return reference_adult_profile(ticks_per_year)
    return qualification_profile()
