from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank

from .elements import WATER_H_MASS_FRACTION, WATER_O_MASS_FRACTION, require_element


ACTIVE_SOIL_ELEMENTS = ("C", "N", "P", "K", "Ca", "Mg", "S", "Fe", "Si")


def _element_pool(seed_bank: SeedBank, x: int, y: int, scale_factor: float = 1.0) -> dict[str, float]:
    stream = seed_bank.stream(f"matter.soil.{x}.{y}")
    baseline = {
        "C": 18.0,
        "N": 4.0,
        "P": 1.2,
        "K": 3.0,
        "Ca": 5.0,
        "Mg": 2.0,
        "S": 1.0,
        "Fe": 7.0,
        "Si": 45.0,
    }
    return {
        symbol: round(value * scale_factor * stream.uniform(0.88, 1.12), 10)
        for symbol, value in baseline.items()
    }


def build_matter_state(*, width: int, height: int, seed_bank: SeedBank, scale_factor: float = 1.0) -> dict:
    cells: list[dict] = []
    for y in range(height):
        for x in range(width):
            cells.append(
                {
                    "x": x,
                    "y": y,
                    "surface_water_kg": 8.0 * scale_factor,
                    "soil_water_kg": 45.0 * scale_factor,
                    "elements_kg": _element_pool(seed_bank, x, y, scale_factor),
                }
            )

    initial_elements = total_elements(cells)
    initial_water = total_water(cells)
    return {
        "width": width,
        "height": height,
        "epoch_applied": -1,
        "water_input_kg": 0.0,
        "water_output_kg": 0.0,
        "initial_water_kg": initial_water,
        "initial_elements_kg": initial_elements,
        "cells": cells,
    }


def total_water(cells: list[dict]) -> float:
    return sum(float(c["surface_water_kg"]) + float(c["soil_water_kg"]) for c in cells)


def total_elements(cells: list[dict]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for cell in cells:
        for symbol, amount in cell["elements_kg"].items():
            require_element(symbol)
            totals[symbol] = totals.get(symbol, 0.0) + float(amount)
    return {symbol: round(value, 10) for symbol, value in sorted(totals.items())}


def water_element_mass(water_kg: float) -> dict[str, float]:
    if water_kg < 0:
        raise ValueError("water mass must be non-negative")
    return {
        "H": water_kg * WATER_H_MASS_FRACTION,
        "O": water_kg * WATER_O_MASS_FRACTION,
    }


def copy_state(state: dict) -> dict:
    return deepcopy(state)
