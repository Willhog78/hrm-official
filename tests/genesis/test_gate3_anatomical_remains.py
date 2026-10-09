"""Conservation and legacy replay checks for opt-in anatomical remains."""
from copy import deepcopy
import math

from hrm_genesis.ecology import animals as a


def _body(animal_id="prey"):
    return {
        "id": animal_id, "species": "grazer", "x": 0, "y": 0,
        "body_elements_kg": {symbol: 0.1 for symbol in a.ANIMAL_TRACKED_ELEMENTS},
        "body_water_kg": 2.0,
    }


def _state():
    return {
        "animals": [_body()],
        "carcass_cells": [{"x": 0, "y": 0, "elements_kg": a._blank_elements(),
                           "fresh_elements_kg": a._blank_elements(), "water_kg": 0.0}],
        "cumulative_deaths_by_cause": {},
    }


def test_new_remains_partitions_conserve_every_element_and_water():
    before = _state()
    original = a.consumer_element_totals(before)
    state = a.enable_anatomical_remains(before)
    assert "anatomical_remains" not in before["carcass_cells"][0]
    assert a.kill_animal(state, "prey", "old_age")
    remains = state["carcass_cells"][0]["anatomical_remains"][0]
    assert set(remains["parts_elements_kg"]) == set(a.ANATOMICAL_DRY_FRACTIONS)
    assert math.isclose(sum(a.ANATOMICAL_DRY_FRACTIONS.values()), 1.0, abs_tol=1e-12)
    assert a.consumer_element_totals(state) == original
    assert a.consumer_water_total_kg(state) == 2.0
    assert a.kill_animal(state, "prey", "old_age") is None
    assert len(state["carcass_cells"][0]["anatomical_remains"]) == 1


def test_legacy_carcasses_remain_unpartitioned_after_opt_in():
    state = _state()
    a.kill_animal(state, "prey", "old_age")
    old = deepcopy(state["carcass_cells"][0])
    new_state = a.enable_anatomical_remains(state)
    assert new_state["carcass_cells"][0]["elements_kg"] == old["elements_kg"]
    assert new_state["carcass_cells"][0]["fresh_elements_kg"] == old["fresh_elements_kg"]
    assert new_state["carcass_cells"][0]["anatomical_remains"] == []


def test_predation_residual_is_partitioned_without_double_counting():
    state = a.enable_anatomical_remains(_state())
    prey = state["animals"][0]
    predator = _body("hunter")
    predator["species"] = "predator"
    # Use a valid predator species and enough mass to exercise the assimilation path.
    predator["species"] = next(name for name in a.SPECIES if a.trait_for(name).trophic_role == "predator")
    state["animals"].append(predator)
    before = a.consumer_element_totals(state)
    water_before = a.consumer_water_total_kg(state)
    a._consume_prey(predator, prey, state["carcass_cells"][0], state)
    state["animals"].remove(prey)
    after = a.consumer_element_totals(state)
    for element in before:
        assert math.isclose(before[element], after[element], abs_tol=1e-10)
    assert math.isclose(a.consumer_water_total_kg(state), water_before, abs_tol=1e-10)
