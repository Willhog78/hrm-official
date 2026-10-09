"""MICRO: one energy store for eating, hand-feeding and nursing
(child_energy_store "size-scaled-v1"; docs/architecture/CHILD_ENERGY_STORE.md)."""

from __future__ import annotations

import pytest

from _scenario import Scenario, el
from hrm_genesis.human.biology import (
    ENERGY_STORE_SIZE_SCALED,
    NURSING_DEMAND_LIMITED,
    _age_profile,
    _provision_dependent,
    energy_store_capacity,
)
from hrm_genesis.human.diet import ingest_pool

AGE_DAYS = 3 * 365  # weaned enough to feed itself; still nursed


def _child(sc: Scenario, energy: float) -> dict:
    scale = 0.05 + 0.95 * AGE_DAYS / (18 * 365)
    return sc.add_agent(
        "human-b00000001", 0, 0, age_ticks=AGE_DAYS, caregiver_id=sc.agent["id"], energy=energy,
        body_elements_kg=el(28.0 * scale), body_water_kg=42.0 * scale, generation=1, sex="male",
    )


def _store_profile(sc, human):
    profile = dict(_age_profile(human, sc.profile))
    profile["energy_store_capacity_kcal"] = energy_store_capacity(profile)
    return profile


def test_store_is_size_scaled_for_children_and_unchanged_for_adults():
    sc = Scenario(width=3)
    mother = sc.set_agent(0, 0, sex="female")
    child = _child(sc, 100.0)
    adult = _age_profile(mother, sc.profile)
    young = _age_profile(child, sc.profile)
    assert energy_store_capacity(adult) == pytest.approx(float(sc.profile["energy_capacity_kcal"]))
    assert energy_store_capacity(young) == pytest.approx(
        float(sc.profile["energy_capacity_kcal"]) * young["development_scale"])


def test_eating_beyond_the_store_is_refused_and_recorded_not_credited():
    sc = Scenario(width=3)
    sc.set_agent(0, 0, sex="female")
    child = _child(sc, 0.0)
    profile = _store_profile(sc, child)
    store = profile["energy_store_capacity_kcal"]
    child["energy"] = store - 100.0
    pool = el(50.0)
    detritus = el(0.0)
    rec = ingest_pool(child, "plant_tissue", 1.0, pool, detritus, profile)
    assert rec["kg"] == pytest.approx(1.0)  # the food is eaten, as before
    assert child["energy"] == pytest.approx(store)
    assert rec["refused_kcal"] == pytest.approx(rec["kcal"] - 100.0)


def test_legacy_eating_keeps_the_adult_cap_and_records_nothing():
    sc = Scenario(width=3)
    sc.set_agent(0, 0, sex="female")
    child = _child(sc, 0.0)
    profile = _age_profile(child, sc.profile)
    child["energy"] = energy_store_capacity(profile) - 100.0
    rec = ingest_pool(child, "plant_tissue", 1.0, el(50.0), el(0.0), profile)
    assert "refused_kcal" not in rec
    assert child["energy"] > energy_store_capacity(profile)  # above its own store: the old inconsistency


def test_nursing_never_cuts_back_a_child_on_the_one_store():
    sc = Scenario(width=3)
    mother = sc.set_agent(0, 0, sex="female")
    mother["energy"] = 20000.0
    child = _child(sc, 0.0)
    profile = _store_profile(sc, child)
    ingest_pool(child, "plant_tissue", 5.0, el(50.0), el(0.0), profile)
    before = float(child["energy"])
    stats = {}
    _provision_dependent(child, mother, profile, NURSING_DEMAND_LIMITED, stats)
    assert stats.get("child_store_clamp_kcal", 0.0) == 0.0
    assert float(child["energy"]) >= before


def test_a_day_in_the_world_records_refused_energy_by_age_class():
    sc = Scenario(capacities=True, width=3)
    mother = sc.agent
    mother["energy"] = float(sc.profile["energy_capacity_kcal"])  # full: her meal is refused energy
    sc.set_pool(0, 0, "plant_elements_kg", 50000.0)
    sc.set_water(0, 0, 50000.0)
    sc.humans["energy_store_model"] = ENERGY_STORE_SIZE_SCALED
    sc.step(1)
    refused = sc.humans["energy_store_stats"]["refused_kcal"]
    assert refused.get("adult", 0.0) > 0.0
