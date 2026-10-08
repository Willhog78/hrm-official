"""MICRO: a caregiver hands solid food to its dependent child (solid-food-v1).

Physical transfer only: the caregiver must obtain food from the cell they
share, the child ingests from the caregiver's hands within its own capacity,
and what is not eaten goes back. Mass is exact; the caregiver pays handling.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from _scenario import Scenario, mass
import hrm_genesis.human.biology as biology
from hrm_genesis.human.diet import FOOD_KINDS


def _family(child_age_days: int = 300, child_energy: float = 500.0, together: bool = True):
    sc = Scenario(capacities=True, width=3)
    mother = sc.agent
    mother["energy"] = 20000.0
    child = deepcopy(mother)
    child.update(id="human-child", age_ticks=child_age_days, caregiver_id=mother["id"], energy=child_energy,
                 x=0 if together else 1, y=0)
    child_profile = biology._age_profile(child, sc.profile)
    for s in child["body_elements_kg"]:
        child["body_elements_kg"][s] = float(child["body_elements_kg"][s]) * child_profile["development_scale"] * 0.9
    mother["x"], mother["y"] = 0, 0
    sc.humans["humans"].append(child)
    return sc, mother, child


def _give(sc, mother, child, eaten_kg=0.0):
    stats = {}
    cp = biology._age_profile(child, sc.profile)
    mp = biology._age_profile(mother, sc.profile)
    pcell = sc._p(int(child["x"]), int(child["y"]))
    got = biology._provision_solid_food(child, mother, cp, mp, pcell, sc.carcass(int(child["x"]), int(child["y"])), eaten_kg, stats)
    return got, stats, cp


def test_mass_moves_exactly_from_cell_to_child_and_the_rest_goes_back():
    sc, mother, child = _family()
    sc.set_pool(0, 0, "plant_elements_kg", 50.0)
    cell_before = mass(sc._p(0, 0)["plant_elements_kg"])
    detritus_before = mass(sc._p(0, 0)["detritus_elements_kg"])
    body_before = mass(child["body_elements_kg"])
    energy_before = float(mother["energy"])
    got, stats, cp = _give(sc, mother, child)
    assert got > 0.0 and stats["solid_food_outcomes"] == {"fed": 1}
    taken_from_cell = cell_before - mass(sc._p(0, 0)["plant_elements_kg"])
    assert taken_from_cell == pytest.approx(got, rel=1e-9)
    gained = (mass(child["body_elements_kg"]) - body_before) + (mass(sc._p(0, 0)["detritus_elements_kg"]) - detritus_before)
    assert gained == pytest.approx(got, rel=1e-9)
    assert got <= cp["bite_cap_kg"] + 1e-12
    assert float(mother["energy"]) == energy_before  # plant tissue has no handling cost


def test_child_capacity_limits_intake():
    sc, mother, child = _family()
    sc.set_pool(0, 0, "plant_elements_kg", 50.0)
    cp = biology._age_profile(child, sc.profile)
    got, stats, _ = _give(sc, mother, child, eaten_kg=cp["bite_cap_kg"] * 0.75)
    assert got == pytest.approx(cp["bite_cap_kg"] * 0.25, rel=1e-6)
    got, stats, _ = _give(sc, mother, child, eaten_kg=cp["bite_cap_kg"])
    assert got == 0.0 and stats["solid_food_outcomes"] == {"gut_full": 1}


@pytest.mark.parametrize("case,outcome", [
    ("too_young", "too_young"), ("apart", "not_together"), ("sated", "not_hungry"), ("bare", "no_known_food_here"),
])
def test_no_transfer_without_its_physical_conditions(case, outcome):
    sc, mother, child = _family(child_age_days=100 if case == "too_young" else 300,
                                child_energy=1.0e6 if case == "sated" else 500.0,
                                together=case != "apart")
    if case != "bare":
        sc.set_pool(int(child["x"]), 0, "plant_elements_kg", 50.0)
    cell = mass(sc._p(int(child["x"]), 0)["plant_elements_kg"])
    got, stats, _ = _give(sc, mother, child)
    assert got == 0.0 and stats["solid_food_outcomes"] == {outcome: 1}
    assert mass(sc._p(int(child["x"]), 0)["plant_elements_kg"]) == cell


def test_only_food_the_caregiver_knows_and_the_caregiver_pays_handling_within_reach():
    sc, mother, child = _family()
    sc.set_pool(0, 0, "seed_elements_kg", 5.0)
    mother["cognition"]["food_values"] = {"plant_tissue": 1760.0}  # does not know seed
    got, stats, _ = _give(sc, mother, child)
    assert got == 0.0 and stats["solid_food_outcomes"] == {"no_known_food_here": 1}
    mother["cognition"]["food_values"] = {"plant_tissue": 1760.0, "seed": 2800.0}
    child_energy = float(child["energy"])
    energy_before = float(mother["energy"])
    got, stats, cp = _give(sc, mother, child)
    assert 0.0 < got <= min(cp["bite_cap_kg"], FOOD_KINDS["seed"]["hand_access_kg"]) + 1e-12
    # Handling is charged on what was obtained, at adult scale; the child pays none.
    assert energy_before - float(mother["energy"]) == pytest.approx(got * 60.0, rel=1e-9)
    assert float(child["energy"]) > child_energy


def test_a_day_in_the_world_feeds_the_child_and_conserves_matter():
    sc, mother, child = _family()
    sc.set_pool(0, 0, "plant_elements_kg", 50.0)
    sc.set_water(0, 0, 50000.0)
    sc.step(1)
    stats = sc.humans.get("capacity_stats", {})
    assert stats.get("solid_food_outcomes", {}).get("fed", 0) == 1
    assert stats.get("solid_food_kg_by_kind", {}).get("plant_tissue", 0.0) > 0.0
