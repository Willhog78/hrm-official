"""G10.5 reference-v2 physiology: energy-budget realism."""

from __future__ import annotations

from copy import deepcopy

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.biology import _age_profile, _catabolize_lean_tissue, _provision_dependent, evolve_humans
from hrm_genesis.human.calibration import reference_adult_profile, reference_adult_profile_v2


def _config(version: str) -> GenesisConfig:
    return GenesisConfig(
        master_seed="g10-5-fast", world_width=4, world_height=4, ticks_per_year=365,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, human_biology_enabled=True,
        material_scale_factor=1000.0, human_calibration_enabled=True, agentus_physiology_version=version,
    )


def _days_to_starve(version: str) -> tuple[int, str, float]:
    sim = GenesisSimulation(_config(version))
    humans, producers, matter = sim.human_state(), sim.ecology_state(), sim.matter_state()
    world, consumers = sim.world_state(), {"animals": [], "carcass_cells": []}
    for person in humans["humans"]:
        person["age_ticks"] = 25 * 365  # adults, no reproduction interference
        person["sex"] = "male"
    start_mass = None
    for day in range(1, 200):
        for cell in producers["cells"]:
            for pool in ("plant_elements_kg", "seed_elements_kg"):
                cell[pool] = {s: 0.0 for s in cell[pool]}
        for cell in matter["cells"]:
            cell["surface_water_kg"] = max(cell["surface_water_kg"], 1e6)
        before = sum(sum(h["body_elements_kg"].values()) for h in humans["humans"])
        detritus_before = sum(sum(c["detritus_elements_kg"].values()) for c in producers["cells"])
        start_mass = start_mass or before
        humans, producers, matter = evolve_humans(humans, producers, matter, world, day, consumer_state=consumers)
        records = humans.get("death_records", [])
        if records:
            return day, records[0]["cause"], start_mass
    return 999, "none", start_mass


def test_fasting_adult_survives_weeks_in_v2_and_days_in_v1():
    v1_days, _, _ = _days_to_starve("reference-v1")
    v2_days, cause, _ = _days_to_starve("reference-v2")
    assert v1_days <= 5
    assert 45 <= v2_days <= 75, v2_days  # ~30 days of fat + ~28 days of lean tissue
    assert cause in {"low_body_mass", "energy"}


def test_lean_catabolism_conserves_mass_and_covers_the_deficit():
    profile = reference_adult_profile_v2(365)
    human = {"energy": -8000.0, "body_elements_kg": {"C": 24.0, "N": 2.24, "K": 0.7, "P": 0.336, "Mg": 0.364, "S": 0.28}}
    detritus = {s: 0.0 for s in human["body_elements_kg"]}
    before = sum(human["body_elements_kg"].values())
    taken = _catabolize_lean_tissue(human, profile, detritus)
    assert abs(taken - 2.0) < 1e-9 and human["energy"] == 0.0
    assert abs(sum(human["body_elements_kg"].values()) + sum(detritus.values()) - before) < 1e-9


def test_lactation_draws_on_reserve_tapers_and_costs_the_mother_more():
    base = reference_adult_profile_v2(365)
    child = {"id": "c", "x": 0, "y": 0, "age_ticks": 60, "energy": 100.0, "body_water_kg": 2.0,
             "body_elements_kg": {"C": 1.0, "N": 0.1, "K": 0.03, "P": 0.01, "Mg": 0.01, "S": 0.01}}
    profile = _age_profile(child, base)
    rich = {"id": "m", "x": 0, "y": 0, "energy": 60000.0, "body_water_kg": 42.0,
            "body_elements_kg": {"C": 24.0, "N": 2.24, "K": 0.7, "P": 0.336, "Mg": 0.364, "S": 0.28}}
    poor = dict(deepcopy(rich), energy=3000.0)
    c1, c2 = deepcopy(child), deepcopy(child)
    _provision_dependent(c1, rich, profile)
    _provision_dependent(c2, poor, profile)
    given_rich = c1["energy"] - 100.0
    assert abs(given_rich - 550.0) < 1e-6
    assert abs((60000.0 - rich["energy"]) - 550.0 / 0.8) < 1e-6
    assert 0.0 < c2["energy"] - 100.0 < given_rich  # tapered, not cut off


def test_child_metabolism_scales_with_size_to_the_three_quarters():
    v1, v2 = reference_adult_profile(365), reference_adult_profile_v2(365)
    infant = {"age_ticks": 90}
    p1, p2 = _age_profile(infant, v1), _age_profile(infant, v2)
    scale = p2["development_scale"]
    assert abs(p2["basal_energy_kcal_per_tick"] - 2000.0 * scale ** 0.75) < 1e-9
    assert p2["basal_energy_kcal_per_tick"] > p1["basal_energy_kcal_per_tick"] * 0.9
    adult = {"age_ticks": 30 * 365}
    assert _age_profile(adult, v2)["basal_energy_kcal_per_tick"] == 2000.0


def test_v2_run_conserves_matter_and_replays():
    import sys
    sys.path.insert(0, "qualification/genesis")
    from run_g5_human_biology_gate import combined_element_errors, combined_water_error

    cfg = GenesisConfig(
        master_seed="g10-5-run", world_width=8, world_height=8, ticks_per_year=365,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, human_biology_enabled=True,
        human_cognition_enabled=True, human_actions_enabled=True, multi_population_enabled=True,
        material_scale_factor=1000.0, human_calibration_enabled=True, agentus_physiology_version="reference-v2",
    )
    a, b = GenesisSimulation(cfg), GenesisSimulation(cfg)
    a.run(30)
    b.run(30)
    assert a.ledger.digest() == b.ledger.digest() and a.ledger.verify_chain()
    assert max(abs(v) for v in combined_element_errors(a).values()) < 1e-6
    assert abs(combined_water_error(a)) < 1e-6
    assert cfg.canonical()["agentus_physiology_version"] == "reference-v2"
    assert "agentus_physiology_version" not in GenesisConfig(**{**cfg.__dict__, "agentus_physiology_version": "reference-v1"}).canonical()
