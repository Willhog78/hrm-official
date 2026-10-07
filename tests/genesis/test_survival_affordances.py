from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.plants import (
    build_producer_state,
    evolve_producers,
    producer_woody_biomass_kg,
    seed_initial_producers,
)
from hrm_genesis.human.biology import _apply_physiology
from hrm_genesis.matter.pools import build_matter_state


def test_terrain_shelter_requires_exposed_rock_and_relief():
    world = GenesisSimulation(
        GenesisConfig(master_seed="survival-terrain", world_width=16, world_height=16)
    ).world_state()

    sheltered = [c for c in world["cells"] if float(c["natural_shelter"]) > 0.0]
    assert sheltered
    assert all(float(c["rock_exposure"]) >= 0.58 for c in sheltered)
    assert all(float(c["terrain_relief"]) >= 12.0 for c in sheltered)


def test_woody_biomass_requires_sustained_viable_growth_conditions():
    seed_bank = SeedBank("survival-wood")
    matter = build_matter_state(width=4, height=4, seed_bank=seed_bank, scale_factor=1000.0)
    producers = build_producer_state(width=4, height=4)
    matter, producers = seed_initial_producers(
        matter,
        producers,
        seed_bank,
        biomass_scale_factor=1000.0,
    )

    viable_world = {
        "cells": [
            {"x": x, "y": y, "solar": 1.0, "temperature": 22.0, "precipitation": 0.0}
            for y in range(4)
            for x in range(4)
        ]
    }
    for cell in matter["cells"]:
        cell["soil_water_kg"] = max(float(cell["soil_water_kg"]), 10000.0)

    for epoch in range(45):
        producers, matter = evolve_producers(producers, matter, viable_world, epoch)

    assert producer_woody_biomass_kg(producers) > 0.0

    seed_bank = SeedBank("survival-no-wood")
    dry_matter = build_matter_state(width=4, height=4, seed_bank=seed_bank, scale_factor=1000.0)
    dry_producers = build_producer_state(width=4, height=4)
    dry_matter, dry_producers = seed_initial_producers(
        dry_matter,
        dry_producers,
        seed_bank,
        biomass_scale_factor=1000.0,
    )
    impossible_world = deepcopy(viable_world)
    for cell in impossible_world["cells"]:
        cell["solar"] = 0.0

    for epoch in range(45):
        dry_producers, dry_matter = evolve_producers(
            dry_producers,
            dry_matter,
            impossible_world,
            epoch,
        )

    assert producer_woody_biomass_kg(dry_producers) == 0.0


def test_physical_cover_reduces_heat_exposure_without_named_shelter_action():
    profile = {
        "calibrated": True,
        "water_capacity_kg": 42.0,
    }
    exposed = {
        "energy": 8000.0,
        "body_water_kg": 42.0,
        "fatigue": 0.0,
        "injury": 0.0,
        "core_temperature_c": 37.0,
    }
    protected = deepcopy(exposed)
    hot_exposed = {"temperature": 60.0, "natural_shelter": 0.0}
    hot_protected = {"temperature": 60.0, "natural_shelter": 0.8}

    _apply_physiology(exposed, hot_exposed, moved=False, profile=profile)
    _apply_physiology(
        protected,
        hot_protected,
        moved=False,
        profile=profile,
        producer_cell={"woody_elements_kg": {"C": 8.0}},
    )

    assert float(protected["energy"]) > float(exposed["energy"])
    assert float(protected["body_water_kg"]) >= float(exposed["body_water_kg"])
    assert float(protected["injury"]) <= float(exposed["injury"])
