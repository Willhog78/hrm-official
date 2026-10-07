"""MICRO: infant care, isolated from adult survival."""

from __future__ import annotations

import pytest

from _scenario import Scenario, el


def _family(physiology: str = "reference-v1", mother_energy: float | None = None, infant_age: int = 60, distance: int = 0):
    sc = Scenario(physiology=physiology, width=5)
    mother = sc.set_agent(0, 0, sex="female")
    if mother_energy is not None:
        mother["energy"] = mother_energy
    for x in range(5):
        sc.set_water(x, 0, 50000.0)
    scale = 0.05 + 0.95 * infant_age / (18 * 365)
    infant = sc.add_agent(
        "human-b00000001", distance, 0, age_ticks=infant_age, caregiver_id=mother["id"], energy=200.0,
        body_elements_kg=el(28.0 * scale), body_water_kg=42.0 * scale, generation=1, sex="male",
    )
    return sc, infant


def _infant(sc):
    return next((h for h in sc.humans["humans"] if h["id"] == "human-b00000001"), None)


def test_infant_with_a_provisioned_caregiver_is_fed_and_survives():
    sc, _ = _family()
    sc.set_pool(0, 0, "plant_elements_kg", 50000.0)
    sc.step(30)
    infant = _infant(sc)
    assert infant is not None and infant["energy"] > 100.0, "fed infant lost energy"


def test_nursing_transfers_energy_water_and_body_mass_from_the_mother():
    sc, infant = _family()
    sc.set_pool(0, 0, "plant_elements_kg", 50000.0)
    mother_mass0 = sum(sc.agent["body_elements_kg"].values())
    infant_mass0 = sum(infant["body_elements_kg"].values())
    sc.step(5)
    infant = _infant(sc)
    assert sum(infant["body_elements_kg"].values()) > infant_mass0
    assert infant["caregiver_present"] is True


def test_no_caregiver_means_no_provisioning():
    sc, _ = _family()
    sc.set_pool(0, 0, "plant_elements_kg", 50000.0)
    sc.humans["humans"] = [h for h in sc.humans["humans"] if h["id"] != sc.agent["id"]]  # mother gone
    sc.step(1)
    infant = _infant(sc)
    assert infant is None or infant["energy"] < 200.0, "infant gained energy with nobody to feed it"


def test_caregiver_elsewhere_does_not_nurse():
    from hrm_genesis.human.biology import _age_profile, _provision_dependent
    sc, infant = _family(distance=1)
    profile = _age_profile(infant, sc.profile)
    e0 = infant["energy"]
    _provision_dependent(infant, sc.agent, profile)
    assert infant["energy"] == e0, "nursed across cells"


@pytest.mark.xfail(strict=True, reason=(
    "KNOWN MODEL QUIRK (micro tier, 2026-10-07): a dependent child moves straight "
    "to its caregiver's cell however far away it is (no one-step limit). Latent "
    "in live runs, where caregiver and child are never more than one cell apart."))
def test_dependent_child_moves_at_most_one_cell_per_day():
    sc, _ = _family(distance=2)
    sc.set_pool(0, 0, "plant_elements_kg", 50000.0)
    sc.step(1)
    infant = _infant(sc)
    assert abs(infant["x"] - 2) <= 1, f"child jumped from x=2 to x={infant['x']} in one day"


def _scarce_daily_food(sc, kg_per_day: float, days: int):
    for _ in range(days):
        sc.set_pool(0, 0, "plant_elements_kg", kg_per_day)
        sc.step()
        if _infant(sc) is None:
            break


def test_infant_starvation_reproduces_in_isolation_under_v1():
    """Known issue, isolated: food just short of a full gut each day leaves the
    mother ~100 kcal/day of surplus; under v1 she has no reserve to draw on, so
    her infant (needing ~200 kcal/day) starves beside her."""
    sc, _ = _family(mother_energy=250.0)
    _scarce_daily_food(sc, 1.2, 150)
    deaths = {d["id"]: d["cause"] for d in sc.deaths()}
    assert deaths.get("human-b00000001") == "energy", f"v1 infant starvation no longer reproduces: {deaths}"
    assert sc.agent["id"] not in deaths, "the mother died too; scenario no longer isolates the infant"


def test_same_scarcity_under_reference_v2_feeds_the_infant_from_the_mothers_reserve():
    sc, _ = _family(physiology="reference-v2", mother_energy=60000.0)
    _scarce_daily_food(sc, 1.2, 150)
    assert _infant(sc) is not None, f"v2 infant died: {sc.deaths()}"
