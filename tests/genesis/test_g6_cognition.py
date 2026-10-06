from hrm_genesis.human.planning import choose_destination


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
