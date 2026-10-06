from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank

from .climate import precipitation_amount, temperature_c
from .energy import solar_input
from .grid import build_grid
from .soil import diffuse_nutrients
from .terrain import latitude_factor
from .water import apply_hydrology


def build_world_state(
    *,
    width: int,
    height: int,
    ticks_per_year: int,
    master_seed: str,
    seed_bank: SeedBank,
) -> dict:
    cells = build_grid(width, height, seed_bank)
    initial_water = sum(float(c["surface_water"]) + float(c["soil_moisture"]) for c in cells)
    initial_nutrients = sum(float(c["nutrients"]) for c in cells)
    return {
        "width": width,
        "height": height,
        "ticks_per_year": ticks_per_year,
        "master_seed": master_seed,
        "epoch_applied": -1,
        "water_input": 0.0,
        "water_output": 0.0,
        "initial_water": initial_water,
        "initial_nutrients": initial_nutrients,
        "cells": cells,
    }


def evolve_world(state: dict, epoch: int) -> dict:
    world = deepcopy(state)
    width = int(world["width"])
    height = int(world["height"])
    ticks_per_year = int(world["ticks_per_year"])
    seed = str(world["master_seed"])
    cells = world["cells"]

    precipitation_total = 0.0
    for cell in cells:
        y = int(cell["y"])
        lat = latitude_factor(y, height)
        cell["solar"] = solar_input(epoch, ticks_per_year, lat)
        cell["temperature"] = temperature_c(
            epoch=epoch,
            ticks_per_year=ticks_per_year,
            y=y,
            height=height,
            elevation=float(cell["elevation"]),
        )
        cell["precipitation"] = precipitation_amount(
            seed=seed,
            epoch=epoch,
            ticks_per_year=ticks_per_year,
            x=int(cell["x"]),
            y=y,
            height=height,
            elevation=float(cell["elevation"]),
        )
        precipitation_total += float(cell["precipitation"])

    evaporation, boundary_loss = apply_hydrology(cells, width, height)
    diffuse_nutrients(cells, width, height)

    world["water_input"] = float(world["water_input"]) + precipitation_total
    world["water_output"] = float(world["water_output"]) + evaporation + boundary_loss
    world["epoch_applied"] = epoch

    for cell in cells:
        for field in (
            "temperature",
            "solar",
            "precipitation",
            "surface_water",
            "soil_moisture",
            "nutrients",
        ):
            cell[field] = round(float(cell[field]), 10)
    world["water_input"] = round(float(world["water_input"]), 10)
    world["water_output"] = round(float(world["water_output"]), 10)
    return world


def water_balance_error(state: dict) -> float:
    stored = sum(float(c["surface_water"]) + float(c["soil_moisture"]) for c in state["cells"])
    expected = float(state["initial_water"]) + float(state["water_input"]) - float(state["water_output"])
    return stored - expected


def nutrient_balance_error(state: dict) -> float:
    stored = sum(float(c["nutrients"]) for c in state["cells"])
    return stored - float(state["initial_nutrients"])
