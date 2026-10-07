from hrm_genesis.human.planning import choose_destination


def test_hungry_agent_selects_visible_food_over_surplus_water_and_old_reward():
    perception = {
        "origin": [0, 0], "forage_need_kg": 1.14, "energy_reserve_fraction": 0.05,
        "cells": [
            {"x": 0, "y": 0, "food_kg": 0.0, "water_kg": 1000000.0},
            {"x": 1, "y": 0, "food_kg": 1.35, "water_kg": 42.0},
        ],
    }
    assert choose_destination({}, perception, {
        "expectations": {"0,0": 1000.0}, "uncertainty": 0.05,
    }) == (1, 0)


def test_hungry_agent_explores_when_visible_food_cannot_support_a_day():
    perception = {
        "origin": [0, 0], "forage_need_kg": 1.14, "energy_reserve_fraction": 0.05,
        "cells": [
            {"x": 0, "y": 0, "food_kg": 0.0, "water_kg": 42.0},
            {"x": 1, "y": 0, "food_kg": 0.0, "water_kg": 42.0},
        ],
    }
    assert choose_destination({}, perception, {}) == (1, 0)


def test_different_histories_change_choice_under_same_perception():
    perception = {
        "origin": [1, 1],
        "recognized": [],
        "cells": [
            {"x": 0, "y": 1, "food_kg": 1.0, "water_kg": 1.0},
            {"x": 2, "y": 1, "food_kg": 1.0, "water_kg": 1.0},
        ],
    }
    human = {"x": 1, "y": 1}

    left = choose_destination(
        human,
        perception,
        {"expectations": {"0,1": 4.0, "2,1": -1.0}, "uncertainty": 0.1},
    )
    right = choose_destination(
        human,
        perception,
        {"expectations": {"0,1": -1.0, "2,1": 4.0}, "uncertainty": 0.1},
    )

    assert left == (0, 1)
    assert right == (2, 1)
    assert left != right
