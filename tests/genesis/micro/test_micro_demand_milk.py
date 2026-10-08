"""MICRO: demand-limited milk (nursing_model "demand-limited-v1").

What the child can receive (room in its size-scaled store) is fixed before any
milk is made. The mother makes only that, pays for what she makes including the
stated conversion loss, and nothing produced goes unaccounted.
"""

from __future__ import annotations

import pytest

from _scenario import Scenario, el
from hrm_genesis.config import GenesisConfig
from hrm_genesis.human.biology import (
    NURSING_DEMAND_LIMITED,
    NURSING_SUPPLY_CAPPED_LEGACY,
    _age_profile,
    _provision_dependent,
)


def _pair(physiology: str = "reference-v1", child_energy: float = 200.0, mother_energy: float = 20000.0):
    sc = Scenario(physiology=physiology, width=3)
    mother = sc.set_agent(0, 0, sex="female")
    mother["energy"] = mother_energy
    sc.set_water(0, 0, 50000.0)
    scale = 0.05 + 0.95 * 60 / (18 * 365)
    child = sc.add_agent(
        "human-b00000001", 0, 0, age_ticks=60, caregiver_id=mother["id"], energy=child_energy,
        body_elements_kg=el(28.0 * scale), body_water_kg=42.0 * scale, generation=1, sex="male",
    )
    profile = _age_profile(child, sc.profile)
    capacity = float(profile["energy_capacity_kcal"]) * max(0.10, float(profile["development_scale"]))
    return sc, mother, child, profile, capacity


def _nurse(model, **kw):
    sc, mother, child, profile, capacity = _pair(**kw)
    m0, c0, stats = float(mother["energy"]), float(child["energy"]), {}
    _provision_dependent(child, mother, profile, model, stats)
    return m0 - float(mother["energy"]), float(child["energy"]) - c0, stats, profile, capacity, c0


def test_child_near_full_receives_only_its_room_and_the_mother_pays_only_that():
    sc, mother, child, profile, capacity = _pair()
    near_full = capacity - 50.0
    paid, gained, stats, *_ = _nurse(NURSING_DEMAND_LIMITED, child_energy=near_full)
    assert gained == pytest.approx(50.0)
    assert paid == pytest.approx(50.0)  # reference-v1 states no conversion loss
    assert stats["milk_supply_kcal"] == pytest.approx(float(profile["nursing_energy_kcal_per_tick"]))
    assert stats["milk_unabsorbed_kcal"] == 0.0 and stats["nursing_days_demand_limited"] == 1


def test_child_outcome_is_unchanged_and_only_the_mothers_waste_is_removed():
    *_, capacity, _ = _nurse(NURSING_SUPPLY_CAPPED_LEGACY)
    for energy in (100.0, capacity - 50.0):
        legacy_paid, legacy_gained, *_ = _nurse(NURSING_SUPPLY_CAPPED_LEGACY, child_energy=energy)
        paid, gained, *_ = _nurse(NURSING_DEMAND_LIMITED, child_energy=energy)
        assert gained == pytest.approx(legacy_gained)
        assert paid <= legacy_paid
    # Hungry child: the whole supply is made and used, exactly as before.
    legacy_paid, _, *_ = _nurse(NURSING_SUPPLY_CAPPED_LEGACY, child_energy=100.0)
    paid, _, *_ = _nurse(NURSING_DEMAND_LIMITED, child_energy=100.0)
    assert paid == pytest.approx(legacy_paid)


def test_stated_conversion_cost_is_charged_and_its_loss_recorded_as_heat():
    paid, gained, stats, profile, *_ = _nurse(NURSING_DEMAND_LIMITED, physiology="reference-v2", child_energy=100.0)
    efficiency = float(profile["lactation_efficiency"])
    assert gained == pytest.approx(stats["milk_produced_kcal"])
    assert paid == pytest.approx(gained / efficiency)
    assert stats["milk_cost_kcal"] == pytest.approx(stats["milk_produced_kcal"] + stats["milk_conversion_heat_kcal"])
    assert stats["milk_conversion_heat_kcal"] == pytest.approx(gained * (1.0 / efficiency - 1.0))


def test_a_child_already_above_its_store_gets_no_milk_and_the_cut_is_visible():
    sc, mother, child, profile, capacity = _pair()
    paid, gained, stats, *_ = _nurse(NURSING_DEMAND_LIMITED, child_energy=capacity + 30.0)
    assert paid == 0.0 and stats["milk_produced_kcal"] == 0.0
    assert gained == pytest.approx(-30.0) and stats["child_store_clamp_kcal"] == pytest.approx(30.0)


def test_legacy_records_nothing_and_charges_the_full_supply():
    sc, mother, child, profile, capacity = _pair(child_energy=0.0)
    child["energy"] = capacity - 50.0
    m0 = float(mother["energy"])
    _provision_dependent(child, mother, profile)
    assert m0 - float(mother["energy"]) == pytest.approx(float(profile["nursing_energy_kcal_per_tick"]))


def test_a_day_in_the_world_records_milk_when_demand_limited():
    sc, mother, child, profile, capacity = _pair()
    sc.set_pool(0, 0, "plant_elements_kg", 50000.0)
    sc.humans["nursing_model"] = NURSING_DEMAND_LIMITED
    sc.step(1)
    stats = sc.humans["nursing_stats"]
    assert stats["nursing_days"] == 1 and stats["milk_produced_kcal"] > 0.0
    assert stats["milk_absorbed_kcal"] == pytest.approx(stats["milk_produced_kcal"])


def test_fingerprint_key_only_where_behaviour_changes():
    base = dict(master_seed="s", physical_world_enabled=True, matter_enabled=True, producer_ecology_enabled=True,
                consumer_ecology_enabled=True, human_biology_enabled=True, human_calibration_enabled=True,
                ticks_per_year=365, material_scale_factor=1000.0)
    assert GenesisConfig(**base).canonical()["agentus_nursing"] == NURSING_DEMAND_LIMITED
    assert "agentus_nursing" not in GenesisConfig(**base, nursing_model="supply-capped-legacy").canonical()
    uncalibrated = {**base, "human_calibration_enabled": False, "ticks_per_year": 120, "material_scale_factor": 1.0}
    assert "agentus_nursing" not in GenesisConfig(**uncalibrated).canonical()
    with pytest.raises(ValueError):
        GenesisConfig(**base, nursing_model="unlimited")
