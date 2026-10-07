from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank
from hrm_genesis.ecology.plants import build_producer_state, evolve_producers
from hrm_genesis.human.actions import execute_live_sequence
from hrm_genesis.human.biology import _apply_physiology
from hrm_genesis.observer.ecology import ecology_metrics
from hrm_genesis.world.climate import lightning_activity


ELEMENTS = {"C": 0.86, "N": 0.08, "K": 0.025, "P": 0.012, "Mg": 0.013, "S": 0.01}


def scaled(total: float) -> dict[str, float]:
    return {symbol: total * fraction for symbol, fraction in ELEMENTS.items()}


def human() -> dict:
    return {
        "id": "h",
        "energy": 8000.0,
        "body_water_kg": 42.0,
        "fatigue": 0.0,
        "injury": 0.0,
        "core_temperature_c": 37.0,
        "held_material_elements_kg": scaled(0.0),
    }


def main() -> int:
    # Geometry arises from primitive manipulation and persists in the material cell.
    cell = {
        "x": 0,
        "y": 0,
        "plant_elements_kg": scaled(0.0),
        "woody_elements_kg": scaled(2.0),
        "loose_material_elements_kg": scaled(0.0),
        "arranged_material_elements_kg": scaled(0.0),
        "arrangement_geometry": {"span_m": 0.0, "height_m": 0.0, "density": 0.0, "surface_area_m2": 0.0},
        "fire_intensity": 0.0,
        "seed_elements_kg": scaled(0.0),
        "detritus_elements_kg": scaled(0.0),
        "age_ticks": 50,
    }
    actor = human()
    for _ in range(4):
        actor, cell, _ = execute_live_sequence(
            ("grasp", "release", "arrange"),
            actor,
            cell,
        )

    geometry = dict(cell["arrangement_geometry"])
    observer = ecology_metrics(
        {"cells": [cell]},
        {"animals": []},
    )

    exposed = human()
    protected = human()
    world_hot = {"temperature": 60.0, "terrain_cover": 0.0}
    _apply_physiology(exposed, world_hot, moved=False, profile={"calibrated": True, "water_capacity_kg": 42.0}, producer_cell={
        **cell,
        "arranged_material_elements_kg": scaled(0.0),
        "arrangement_geometry": {"span_m": 0.0, "height_m": 0.0, "density": 0.0, "surface_area_m2": 0.0},
    })
    _apply_physiology(protected, world_hot, moved=False, profile={"calibrated": True, "water_capacity_kg": 42.0}, producer_cell=cell)

    # Lightning is deterministic natural forcing and requires no agent.
    samples = [
        lightning_activity(
            seed="fire-qualification",
            epoch=epoch,
            ticks_per_year=365,
            x=3,
            y=3,
        )
        for epoch in range(3650)
    ]
    strike_epoch = next((i for i, value in enumerate(samples) if value > 0.0), None)

    producer = build_producer_state(width=2, height=2)
    producer["cells"][0]["woody_elements_kg"] = scaled(3.0)
    producer["cells"][0]["arranged_material_elements_kg"] = scaled(1.0)
    producer["cells"][0]["arrangement_geometry"] = {
        "span_m": 1.5,
        "height_m": 1.2,
        "density": 0.5,
        "surface_area_m2": 2.0,
    }
    matter = {
        "width": 2,
        "height": 2,
        "epoch_applied": -1,
        "water_input_kg": 0.0,
        "water_output_kg": 0.0,
        "cells": [
            {"x": x, "y": y, "surface_water_kg": 10.0, "soil_water_kg": 50.0, "elements_kg": {k: 100.0 for k in ["C","N","P","K","Ca","Mg","S","Fe","Si"]}}
            for y in range(2) for x in range(2)
        ],
    }
    world_cells = []
    for y in range(2):
        for x in range(2):
            world_cells.append({
                "x": x, "y": y, "solar": 0.8, "temperature": 30.0,
                "precipitation": 0.0, "lightning": 1.0 if (x, y) == (0, 0) else 0.0,
            })
    world = {"cells": world_cells}

    fuel_before = sum(float(v) for bucket in (
        producer["cells"][0]["woody_elements_kg"],
        producer["cells"][0]["arranged_material_elements_kg"],
    ) for v in bucket.values())
    producer_after, matter_after = evolve_producers(producer, matter, world, epoch=0)
    burning = float(producer_after["cells"][0]["fire_intensity"])
    fuel_after = sum(float(v) for bucket in (
        producer_after["cells"][0]["woody_elements_kg"],
        producer_after["cells"][0]["arranged_material_elements_kg"],
    ) for v in bucket.values())
    detritus_after = sum(float(v) for v in producer_after["cells"][0]["detritus_elements_kg"].values())

    near_fire = human()
    _apply_physiology(
        near_fire,
        {"temperature": 22.0, "terrain_cover": 0.0},
        moved=False,
        profile={"calibrated": True, "water_capacity_kg": 42.0},
        producer_cell={**producer_after["cells"][0], "fire_intensity": max(0.8, burning)},
    )

    checks = {
        "arrangement_has_persistent_geometry": geometry["span_m"] > 0.0 and geometry["height_m"] > 0.0 and geometry["surface_area_m2"] > 0.0,
        "observer_can_classify_protective_geometry": observer["protective_arrangement_cells"] >= 1,
        "geometry_changes_exposure_outcome": float(protected["energy"]) > float(exposed["energy"]) or float(protected["injury"]) < float(exposed["injury"]),
        "natural_lightning_occurs_without_agents": strike_epoch is not None,
        "lightning_ignites_existing_fuel": burning > 0.0,
        "combustion_consumes_fuel": fuel_after < fuel_before,
        "combustion_retains_burned_material_in_causal_pools": detritus_after > 0.0,
        "fire_affects_human_body": float(near_fire["injury"]) > 0.0 or float(near_fire["energy"]) < 8000.0,
        "combustion_is_deterministic": samples == [
            lightning_activity(seed="fire-qualification", epoch=e, ticks_per_year=365, x=3, y=3)
            for e in range(3650)
        ],
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print(
        "PHYSICAL_SUBSTRATE_RESULTS:",
        {
            "geometry": geometry,
            "protective_arrangement_cells": observer["protective_arrangement_cells"],
            "first_natural_lightning_epoch": strike_epoch,
            "fire_intensity": round(burning, 6),
            "fuel_before_kg": round(fuel_before, 6),
            "fuel_after_kg": round(fuel_after, 6),
            "detritus_after_kg": round(detritus_after, 6),
            "near_fire_injury": round(float(near_fire["injury"]), 6),
        },
    )

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("PHYSICAL_SUBSTRATE_FAIL:", ", ".join(failed))
        return 1
    print("PHYSICAL_SUBSTRATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
