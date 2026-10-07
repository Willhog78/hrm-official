from hrm_coordination.seeds import SeedBank
from hrm_genesis.ecology.plants import (
    GERMINATION_SEED_MASS_KG,
    SEED_GERMINATION_FRACTION,
    build_producer_state,
    evolve_producers,
)
from hrm_genesis.matter.pools import build_matter_state


VIABLE = {"cells": [{"x": 0, "y": 0, "solar": 1.0, "temperature": 22.0, "precipitation": 0.0}]}


def _single_cell(plant_kg: float, seed_kg: float, age: int):
    matter = build_matter_state(width=1, height=1, seed_bank=SeedBank("plant-age"), scale_factor=1000.0)
    matter["cells"][0]["soil_water_kg"] = 10000.0
    producers = build_producer_state(width=1, height=1)
    cell = producers["cells"][0]
    cell["plant_elements_kg"]["C"] = plant_kg
    cell["seed_elements_kg"]["C"] = seed_kg
    cell["age_ticks"] = age
    return producers, matter


def test_germination_does_not_rejuvenate_established_vegetation():
    producers, matter = _single_cell(plant_kg=30.0, seed_kg=1.0, age=200)
    producers, _ = evolve_producers(producers, matter, VIABLE, 0)
    # 0.002 kg of seedlings joins 30 kg of 200-tick-old vegetation, then ages one tick.
    assert producers["cells"][0]["age_ticks"] == 201


def test_seedlings_in_empty_cell_start_at_age_zero():
    producers, matter = _single_cell(plant_kg=0.0, seed_kg=1.0, age=0)
    producers, _ = evolve_producers(producers, matter, VIABLE, 0)
    assert producers["cells"][0]["age_ticks"] == 1



def _seed_drop(seed_kg: float) -> float:
    producers, matter = _single_cell(plant_kg=0.0, seed_kg=seed_kg, age=0)
    producers, _ = evolve_producers(producers, matter, VIABLE, 0)
    return seed_kg - producers["cells"][0]["seed_elements_kg"]["C"]


def test_small_seed_pool_keeps_fixed_germinating_mass():
    # Seedlings below the 0.02 kg reproduction threshold shed no seed this tick.
    assert abs(_seed_drop(0.05) - GERMINATION_SEED_MASS_KG) < 1e-9


def test_germination_scales_with_large_seed_pool():
    large = 200.0
    # New seedlings (3.3 kg) shed 1.2% back into this single cell's pool.
    assert abs(_seed_drop(large) - 3.3) < 0.1
    assert SEED_GERMINATION_FRACTION == 0.0165
