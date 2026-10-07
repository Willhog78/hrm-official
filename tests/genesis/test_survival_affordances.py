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
from hrm_genesis.human.biology import _apply_physiology, _experienced_reward
from hrm_genesis.human.learning import update_expectations
from hrm_genesis.human.planning import choose_destination
from hrm_genesis.matter.pools import build_matter_state


def test_terrain_shelter_requires_exposed_rock_and_relief():
    world = GenesisSimulation(
        GenesisConfig(master_seed="survival-terrain", world_width=16, world_height=16)
    ).world_state()

    sheltered = [c for c in world["cells"] if float(c["terrain_cover"]) > 0.0]
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
    hot_exposed = {"temperature": 60.0, "terrain_cover": 0.0}
    hot_protected = {"temperature": 60.0, "terrain_cover": 0.8}

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


def test_experienced_protection_can_be_learned_without_a_shelter_rule():
    profile = {
        "calibrated": True,
        "water_capacity_kg": 42.0,
        "basal_energy_kcal_per_tick": 2000.0,
    }
    base = {
        "energy": 8000.0,
        "body_water_kg": 42.0,
        "fatigue": 0.0,
        "injury": 0.0,
        "core_temperature_c": 37.0,
    }

    exposed = deepcopy(base)
    protected = deepcopy(base)
    _apply_physiology(
        exposed,
        {"temperature": 60.0, "terrain_cover": 0.0},
        moved=False,
        profile=profile,
    )
    _apply_physiology(
        protected,
        {"temperature": 60.0, "terrain_cover": 0.8},
        moved=False,
        profile=profile,
        producer_cell={"woody_elements_kg": {"C": 8.0}},
    )

    exposed_reward = _experienced_reward(
        start_energy=8000.0,
        start_water=42.0,
        start_injury=0.0,
        human=exposed,
        profile=profile,
    )
    protected_reward = _experienced_reward(
        start_energy=8000.0,
        start_water=42.0,
        start_injury=0.0,
        human=protected,
        profile=profile,
    )
    assert protected_reward > exposed_reward

    expectations = {}
    expectations = update_expectations(
        expectations,
        {"origin": [0, 0], "cells": []},
        exposed_reward,
    )
    expectations = update_expectations(
        expectations,
        {"origin": [1, 0], "cells": []},
        protected_reward,
    )
    perception = {
        "origin": [0, 0],
        "recognized": [],
        "cells": [
            {"x": 0, "y": 0, "food_kg": 1.0, "water_kg": 1.0},
            {"x": 1, "y": 0, "food_kg": 1.0, "water_kg": 1.0},
        ],
    }
    choice = choose_destination(
        {"x": 0, "y": 0},
        perception,
        {"expectations": expectations, "uncertainty": 0.05},
    )
    assert choice == (1, 0)
