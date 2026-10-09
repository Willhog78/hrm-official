"""Frozen precipitation is stored water and must thaw before runoff."""
from copy import deepcopy

from hrm_genesis.matter.pools import total_water
from hrm_genesis.matter.transfers import apply_water_cycle


def _matter():
    return {"width": 1, "height": 1, "water_scale": 1.0,
            "initial_water_kg": 150.0, "water_input_kg": 0.0, "water_output_kg": 0.0,
            "cells": [{"x": 0, "y": 0, "soil_water_kg": 100.0,
                       "surface_water_kg": 50.0}]}


def _climate(temp, precip):
    return {"cells": [{"x": 0, "y": 0, "temperature": temp, "precipitation": precip,
                       "solar": 0.0, "elevation": 0.0, "wind_speed_m_s": 2.0}]}


def _balanced(state):
    assert abs(total_water(state["cells"]) +
               state["water_output_kg"] - state["initial_water_kg"] -
               state["water_input_kg"]) < 1e-8


def test_frozen_rain_accumulates_then_thaws_conservatively():
    state = apply_water_cycle(_matter(), _climate(-6.0, 10.0))
    assert state["cells"][0]["snow_water_kg"] == 10.0
    assert state["cells"][0]["surface_water_kg"] == 50.0
    _balanced(state)
    warmed = apply_water_cycle(state, _climate(15.0, 0.0))
    assert 0 < warmed["cells"][0]["snow_water_kg"] < 10
    assert warmed["cells"][0]["surface_water_kg"] > state["cells"][0]["surface_water_kg"]
    _balanced(warmed)


def test_legacy_world_remains_rain_only():
    weather = _climate(-10.0, 5.0)
    del weather["cells"][0]["wind_speed_m_s"]
    state = apply_water_cycle(deepcopy(_matter()), weather)
    assert "snow_water_kg" not in state["cells"][0]
    assert state["cells"][0]["surface_water_kg"] > 50.0
    _balanced(state)


def test_snow_is_included_in_full_water_inventory():
    assert total_water([{"surface_water_kg": 3.0, "soil_water_kg": 2.0, "snow_water_kg": 7.0}]) == 12.0
