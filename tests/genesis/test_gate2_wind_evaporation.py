"""Gate 2: moving air changes actual evaporation, not accounting semantics."""
from copy import deepcopy

from hrm_genesis.matter.transfers import apply_water_cycle


def test_wind_evaporation_is_real_bounded_and_conserved():
    # No runoff or infiltration when the soil reservoir is full and only one
    # cell exists. Precipitation is zero, so output equals inventory decrease.
    matter = {"width": 1, "height": 1, "water_scale": 1.0,
              "initial_water_kg": 150.0, "water_input_kg": 0.0, "water_output_kg": 0.0,
              "cells": [{"x": 0, "y": 0, "surface_water_kg": 50.0, "soil_water_kg": 100.0}]}
    climate = {"x": 0, "y": 0, "precipitation": 0.0, "solar": 1.0,
               "temperature": 25.0, "elevation": 0.0}
    calm = apply_water_cycle(deepcopy(matter), {"cells": [climate]})
    windy = apply_water_cycle(deepcopy(matter), {"cells": [dict(climate, wind_speed_m_s=10.0)]})
    strong = apply_water_cycle(deepcopy(matter), {"cells": [dict(climate, wind_speed_m_s=1000.0)]})
    def accounted(state):
        c = state["cells"][0]
        assert abs(c["surface_water_kg"] + c["soil_water_kg"] +
                   state["water_output_kg"] - 150.0) < 1e-8
    for result in (calm, windy, strong):
        accounted(result)
    assert windy["water_output_kg"] > calm["water_output_kg"]
    assert strong["water_output_kg"] <= calm["water_output_kg"] * 1.6000001
    assert calm == apply_water_cycle(deepcopy(matter), {"cells": [climate]})
