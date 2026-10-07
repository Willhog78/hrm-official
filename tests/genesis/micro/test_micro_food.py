"""MICRO: food. Omnivory is a capability; knowing what is food is learned."""

from __future__ import annotations

import pytest

from _scenario import Scenario
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.diet import innate_food_prior


def _hungry(sc: Scenario, x: int, y: int):
    sc.set_agent(x, y, energy=float(sc.profile["energy_capacity_kcal"]) * 0.3)
    sc.set_water(x, y, 50000.0)


def _days_until(sc: Scenario, predicate, limit: int = 40) -> int | None:
    for day in range(1, limit + 1):
        sc.step()
        if sc.agent is None:
            return None
        if predicate(sc):
            return day
    return None


def test_only_plant_tissue_is_known_at_start_including_newborns():
    sc = Scenario(capacities=True)
    prior = innate_food_prior(sc.profile)
    assert sc.agent["cognition"]["food_values"] == prior, sc.agent["cognition"]["food_values"]
    newborn = {"cognition": {"memory": {}}}
    cap.init_capacity_cognition(newborn, sc.profile)
    assert set(newborn["cognition"]["food_values"]) == {"plant_tissue"}


def test_known_plant_tissue_nearby_is_reached_and_eaten():
    sc = Scenario(capacities=True)
    _hungry(sc, 2, 0)
    sc.set_pool(3, 0, "plant_elements_kg", 100.0)
    sc.set_water(3, 0, 50000.0)
    e0 = sc.agent["energy"]
    sc.step()
    assert sc.xy == (3, 0) and sc.pool(3, 0, "plant_elements_kg") < 100.0 and sc.agent["energy"] > e0 - 2000


def test_unknown_seed_is_tasted_survived_and_learned_then_eaten():
    sc = Scenario(capacities=True)
    _hungry(sc, 0, 0)
    sc.set_pool(0, 0, "seed_elements_kg", 200.0)
    sc.set_pool(0, 0, "plant_elements_kg", 100.0)  # enough to stay; isolates learning
    day = _days_until(sc, lambda s: "seed" in s.agent["cognition"]["food_values"])
    assert day is not None, "a hungry agent never sampled seeds lying where it stood"
    assert sc.agent["cognition"]["food_values"]["seed"] > 0.0
    assert sc.xy == (0, 0)
    before = sc.pool(0, 0, "seed_elements_kg")
    sc.step()
    eaten = before - sc.pool(0, 0, "seed_elements_kg")
    assert eaten > 0.1, f"learned seeds are food but ate only {eaten:.3f} kg"


def test_partial_food_is_not_abandoned_for_empty_ground():
    sc = Scenario(capacities=True)
    _hungry(sc, 0, 0)
    sc.agent["cognition"]["food_values"]["seed"] = 2790.0  # already known
    sc.set_pool(0, 0, "seed_elements_kg", 200.0)
    sc.step()
    assert sc.xy == (0, 0), f"left the only food for empty ground: {sc.xy}"


def test_hungry_agent_moves_to_richer_visible_partial_food():
    sc = Scenario(capacities=True)
    _hungry(sc, 0, 0)
    sc.agent["cognition"]["food_values"]["seed"] = 2790.0
    sc.set_pool(0, 0, "seed_elements_kg", 0.05)   # almost nothing here
    sc.set_pool(1, 0, "seed_elements_kg", 200.0)  # a real patch in view
    sc.step()
    assert sc.xy == (1, 0)


def test_a_trickle_below_the_giving_up_level_is_left_to_explore():
    sc = Scenario(capacities=True)
    _hungry(sc, 0, 0)
    sc.agent["cognition"]["food_values"]["seed"] = 2790.0
    sc.set_pool(0, 0, "seed_elements_kg", 0.02)
    sc.step()
    assert sc.xy != (0, 0)


def test_pre_g10_6_abandonment_is_reproduced_with_integrity_off():
    sc = Scenario(capacities=True, integrity=False)
    _hungry(sc, 0, 0)
    sc.agent["cognition"]["food_values"]["seed"] = 2790.0
    sc.set_pool(0, 0, "seed_elements_kg", 200.0)
    sc.step()
    assert sc.xy != (0, 0)


def test_fresh_meat_without_prior_knowledge_is_learned_only_by_tasting():
    sc = Scenario(capacities=True)
    _hungry(sc, 0, 0)
    sc.set_fresh_tissue(0, 0, 5.0)
    assert "fresh_tissue" not in sc.agent["cognition"]["food_values"]
    day = _days_until(sc, lambda s: "fresh_tissue" in s.agent["cognition"]["food_values"])
    assert day is not None
    assert sc.agent["cognition"]["food_values"]["fresh_tissue"] > 0.0


def test_meat_eating_is_seen_only_in_the_same_cell_and_gives_no_value():
    sc = Scenario(capacities=True, width=4)
    _hungry(sc, 0, 0)
    sc.agent["cognition"]["food_values"]["fresh_tissue"] = 4000.0  # eater already knows
    sc.set_fresh_tissue(0, 0, 5.0)
    sc.set_pool(0, 0, "plant_elements_kg", 100.0)  # enough to stay; isolates observation
    near = sc.add_agent("watcher-near", 0, 0)
    far = sc.add_agent("watcher-far", 3, 0)
    near["cognition"]["food_values"] = innate_food_prior(sc.profile)
    far["cognition"]["food_values"] = innate_food_prior(sc.profile)
    sc.step()
    people = {h["id"]: h for h in sc.humans["humans"]}
    # G10.7a: the near watcher saw meat eaten without distress; it does not get
    # a value for meat until it eats some itself.
    assert people["watcher-near"]["cognition"]["observed_ingestion"]["fresh_tissue"]["harmless"] >= 1
    assert "fresh_tissue" not in people["watcher-near"]["cognition"]["food_values"]
    assert "fresh_tissue" not in people["watcher-far"]["cognition"].get("observed_ingestion", {})


def test_rotten_meat_stays_hazardous_and_is_then_avoided():
    sc = Scenario(capacities=True)
    _hungry(sc, 0, 0)
    sc.set_decayed_tissue(0, 0, 5.0)
    day = _days_until(sc, lambda s: "decayed_tissue" in s.agent["cognition"]["food_values"])
    assert day is not None
    assert sc.agent["cognition"]["food_values"]["decayed_tissue"] < 0.0
    assert sc.agent["injury"] > 0.0 or sc.humans["capacity_stats"]["ingestion_hazard"] > 0.0
    before = sum(sc.carcass(0, 0)["elements_kg"].values())
    sc.step(10)
    assert abs(sum(sc.carcass(0, 0)["elements_kg"].values()) - before) < 1e-9, "kept eating rotten meat"


def test_wood_never_becomes_food_even_when_nothing_else_exists():
    sc = Scenario(capacities=True)
    _hungry(sc, 0, 0)
    sc.set_pool(0, 0, "woody_elements_kg", 500.0)
    kcal_from_wood = 0.0
    for _ in range(30):
        sc.step()
        if sc.agent is None:
            break
        kcal_from_wood = sc.humans["capacity_stats"]["intake_kcal_by_kind"].get("woody_tissue", 0.0)
    assert kcal_from_wood == 0.0
    values = (sc.agent or {"cognition": {"food_values": {}}})["cognition"]["food_values"]
    assert values.get("woody_tissue", -1.0) <= 0.0
    eaten = sc.humans["capacity_stats"]["intake_kg_by_kind"].get("woody_tissue", 0.0)
    assert eaten <= 0.2, f"wood eaten repeatedly ({eaten:.2f} kg) despite yielding nothing"
