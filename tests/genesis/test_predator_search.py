"""Search uses bounded local observation, not the world animal registry."""
from copy import deepcopy

import pytest

from hrm_genesis.ecology import animals
from hrm_genesis import GenesisSimulation
from tests.genesis.test_consumer_opportunity import _animal, _world
from qualification.genesis.tier_observer import build_config


def setup():
    c, p, m, w = _world(365, "elapsed-time-v2", 10, 10)
    c["predator_search_model"] = "seen-prey-v1"
    hunter = _animal("searcher", "stalker", 4, 4, 10.0)
    c["animals"] = [hunter]
    return hunter, c, p, m, w


def choose(h, c, p, m, epoch=0):
    return animals._choose_predator_destination(h, c, p, m, epoch, set())


def test_hungry_predator_targets_actual_visible_prey():
    h, c, p, m, _ = setup()
    c["animals"].append(_animal("prey", "browser", 6, 4, 10.0))
    assert choose(h, c, p, m) == (6, 4)
    assert h["prey_encounters"] == {"6,4": 0}


def test_sated_predator_stays_in_observed_prey_patch_instead_of_following_plants():
    h, c, p, m, _ = setup()
    h["energy"] = 50.0
    c["animals"].append(_animal("prey", "browser", 6, 4, 10.0))
    for cell in p["cells"]:
        if (cell["x"], cell["y"]) == (4, 5):
            cell["plant_elements_kg"] = {s: 1e6 for s in cell["plant_elements_kg"]}
    assert choose(h, c, p, m) == (4, 4)


def test_offscreen_prey_positions_and_plant_stocks_do_not_steer_search():
    h, c, p, m, _ = setup()
    other = deepcopy((h, c, p, m))
    c["animals"].append(_animal("hidden", "browser", 9, 9, 10.0))
    for cell in p["cells"]:
        cell["plant_elements_kg"] = {s: 1e9 for s in cell["plant_elements_kg"]}
    assert choose(h, c, p, m) == choose(*other)
    assert h["prey_encounters"] == {}


def test_memory_contains_seen_coordinates_not_updated_hidden_positions():
    h, c, p, m, _ = setup()
    prey = _animal("prey", "browser", 6, 4, 10.0)
    c["animals"].append(prey)
    choose(h, c, p, m)
    h["x"], h["y"] = 0, 0
    prey["x"], prey["y"] = 9, 9
    assert choose(h, c, p, m, 1) == (6, 4)
    assert "9,9" not in h["prey_encounters"]


def test_visible_empty_patch_disproves_memory_and_expired_memory_is_removed():
    h, c, p, m, _ = setup()
    h["prey_encounters"] = {"6,4": 0, "9,9": 0}
    choose(h, c, p, m, 1)
    assert h["prey_encounters"] == {"9,9": 0}
    choose(h, c, p, m, 366)
    assert h["prey_encounters"] == {}


def test_dead_or_already_killed_prey_is_not_remembered():
    h, c, p, m, _ = setup()
    c["animals"].append(_animal("killed", "browser", 4, 4, 10.0))
    c["animals"].append(_animal("dead", "browser", 5, 4, 0.0))
    animals._choose_predator_destination(h, c, p, m, 0, {"killed"})
    assert h["prey_encounters"] == {}


def test_thirst_has_priority_only_for_visible_actual_water():
    h, c, p, m, _ = setup()
    h["body_water_kg"] = 0.05
    for cell in m["cells"]:
        cell["surface_water_kg"] = cell["soil_water_kg"] = 0.0
    next(cell for cell in m["cells"] if (cell["x"], cell["y"]) == (4, 5))["surface_water_kg"] = 1.0
    c["animals"].append(_animal("prey", "browser", 6, 4, 10.0))
    assert choose(h, c, p, m) == (4, 5)


def test_search_moves_at_most_one_cell_and_pays_existing_event_cost(monkeypatch):
    h, c, p, m, w = setup()
    h["energy"] = 50.0
    before = h["energy"]
    monkeypatch.setattr(animals, "has_opportunity", lambda *a: True)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 0)
    h = c["animals"][0]
    assert abs(h["x"]-4)+abs(h["y"]-4) == 1
    assert before-h["energy"] == pytest.approx(0.34+0.30*12/365, abs=1e-9)


def test_no_movement_opportunity_means_no_step_or_movement_cost(monkeypatch):
    h, c, p, m, w = setup()
    h["energy"] = 50.0
    monkeypatch.setattr(animals, "has_opportunity", lambda *a: False)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 0)
    h = c["animals"][0]
    assert (h["x"], h["y"]) == (4, 4)
    assert h["energy"] == pytest.approx(50.0-0.30*12/365, abs=1e-9)


def test_search_explores_and_memory_is_bounded():
    h, c, p, m, _ = setup()
    h["predator_search_visits"] = {f"{i%10},{i//10}": i for i in range(60)}
    h["prey_encounters"] = {f"{i%10},{i//10}": 0 for i in range(60)}
    choose(h, c, p, m, 1)
    assert len(h["predator_search_visits"]) <= 32
    assert len(h["prey_encounters"]) <= 16
    h["prey_encounters"] = {}
    c["animals"] = [h]
    positions = {(h["x"], h["y"])}
    for epoch in range(100):
        target = choose(h, c, p, m, epoch+400)
        h["x"], h["y"] = animals._move_one_step((h["x"], h["y"]), target)
        positions.add((h["x"], h["y"]))
    assert len(positions) > 32


def test_newborns_do_not_inherit_search_memory():
    h, c, p, m, _ = setup()
    choose(h, c, p, m)
    child = animals._offspring(h, 99)
    assert "prey_encounters" not in child and "predator_search_visits" not in child


def test_model_is_opt_in_fingerprinted_and_deterministic():
    arm = "v1-remainingmilk-reservepredators"
    old = build_config("agentus-demography-c", arm)
    new = build_config("agentus-demography-c", arm+"-searchpredators")
    assert "predator_search_model" not in old.canonical()
    assert new.canonical()["predator_search_model"] == "seen-prey-v1"
    assert old.fingerprint() != new.fingerprint()
    assert "predator_search_model" not in GenesisSimulation(old).consumer_state()
    assert GenesisSimulation(new).consumer_state()["predator_search_model"] == "seen-prey-v1"
    h, c, p, m, _ = setup()
    copy = deepcopy((h, c, p, m))
    assert choose(h, c, p, m) == choose(*copy)
