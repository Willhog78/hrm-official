"""Water cycle at material scale (docs/architecture/WATER_CYCLE_SCALE.md)."""

from __future__ import annotations

from copy import deepcopy

import pytest

from hrm_genesis import GenesisConfig
from hrm_genesis.ecology.plants import _environment_factors
from hrm_genesis.matter.transfers import apply_water_cycle


def _world(n: int = 3) -> dict:
    cells = [{"x": x, "y": 0, "precipitation": 2.0 + x, "solar": 0.8, "temperature": 18.0, "elevation": 10.0 - x}
             for x in range(n)]
    return {"width": n, "height": 1, "cells": cells}


def _matter(scale: float, n: int = 3, soil: float = 40.0, surface: float = 6.0) -> dict:
    cells = [{"x": x, "y": 0, "soil_water_kg": soil * scale, "surface_water_kg": surface * scale, "elements_kg": {}}
             for x in range(n)]
    state = {"width": n, "height": 1, "water_input_kg": 0.0, "water_output_kg": 0.0, "cells": cells}
    if scale != 1.0:
        state["water_scale"] = scale
    return state


@pytest.mark.parametrize("soil", [40.0, 99.0, 0.5])
def test_a_scaled_world_is_the_unit_world_times_the_scale(soil):
    unit = apply_water_cycle(_matter(1.0, soil=soil), _world())
    big = apply_water_cycle(_matter(1000.0, soil=soil), _world())
    for a, b in zip(unit["cells"], big["cells"]):
        assert b["soil_water_kg"] == pytest.approx(1000.0 * a["soil_water_kg"], rel=1e-9)
        assert b["surface_water_kg"] == pytest.approx(1000.0 * a["surface_water_kg"], rel=1e-9)
    assert big["water_input_kg"] == pytest.approx(1000.0 * unit["water_input_kg"])
    assert big["water_output_kg"] == pytest.approx(1000.0 * unit["water_output_kg"])


def test_without_a_scale_nothing_changes():
    state = _matter(1.0)
    assert apply_water_cycle(deepcopy(state), _world()) == apply_water_cycle(state, _world())
    assert "water_scale" not in state


def test_the_plant_water_threshold_scales_with_the_water():
    w = {"solar": 0.85, "temperature": 22.0}
    assert _environment_factors(w, {"soil_water_kg": 9.0})[2] == pytest.approx(0.5)
    assert _environment_factors(w, {"soil_water_kg": 9000.0}, 1000.0)[2] == pytest.approx(0.5)


def test_fingerprint_key_only_where_behaviour_changes():
    base = dict(master_seed="s", physical_world_enabled=True, matter_enabled=True, ticks_per_year=365)
    assert "water_cycle_scale" not in GenesisConfig(**base).canonical()  # scale 1
    scaled = {**base, "material_scale_factor": 1000.0}
    assert GenesisConfig(**scaled).canonical()["water_cycle_scale"] == "material-v1"
    assert "water_cycle_scale" not in GenesisConfig(**scaled, water_cycle_scale="unscaled-legacy").canonical()
    with pytest.raises(ValueError):
        GenesisConfig(**base, water_cycle_scale="doubled")
