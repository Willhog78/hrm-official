from __future__ import annotations

from copy import deepcopy

from hrm_genesis.ecology.animals import evolve_consumers
from hrm_genesis.ecology.plants import evolve_producers, producer_biomass_kg
from hrm_genesis.matter.transfers import evolve_matter


def regional_biomass(producer_state: dict, *, x_lt: int | None = None, x_ge: int | None = None) -> float:
    total = 0.0
    for cell in producer_state["cells"]:
        x = int(cell["x"])
        if x_lt is not None and not x < x_lt:
            continue
        if x_ge is not None and not x >= x_ge:
            continue
        total += sum(float(v) for v in cell["plant_elements_kg"].values())
    return total


def _force_climate(world: dict, *, precipitation_left: float, precipitation_right: float) -> dict:
    forced = deepcopy(world)
    split = int(forced["width"]) // 2
    for cell in forced["cells"]:
        x = int(cell["x"])
        cell["solar"] = 0.92
        cell["temperature"] = 22.0
        cell["precipitation"] = precipitation_left if x < split else precipitation_right
    return forced


def _drain_left_region(matter: dict) -> dict:
    drained = deepcopy(matter)
    split = int(drained["width"]) // 2
    removed = 0.0
    for cell in drained["cells"]:
        if int(cell["x"]) >= split:
            continue
        removed += float(cell["surface_water_kg"]) + float(cell["soil_water_kg"])
        cell["surface_water_kg"] = 0.0
        cell["soil_water_kg"] = 0.0
    drained["water_output_kg"] = float(drained["water_output_kg"]) + removed
    return drained


def drought_then_recovery(
    *,
    producer_state: dict,
    consumer_state: dict,
    matter_state: dict,
    world_state: dict,
    drought_ticks: int = 60,
    recovery_ticks: int = 120,
) -> dict[str, float]:
    """Controlled perturbation experiment.

    This does not run inside GenesisSimulation and is not a rescue mechanism.
    The drought is an explicit experimental boundary condition. Removed water is
    booked to the declared open-system output, so the perturbation does not
    silently destroy mass.
    """
    producers = deepcopy(producer_state)
    consumers = deepcopy(consumer_state)
    matter = _drain_left_region(matter_state)

    split = int(producers["width"]) // 2
    before_left = regional_biomass(producers, x_lt=split)
    before_right = regional_biomass(producers, x_ge=split)

    drought_world = _force_climate(
        world_state,
        precipitation_left=0.0,
        precipitation_right=1.8,
    )

    for epoch in range(drought_ticks):
        matter = evolve_matter(matter, drought_world, epoch)
        producers, matter = evolve_producers(producers, matter, drought_world, epoch)
        consumers, producers, matter = evolve_consumers(
            consumers, producers, matter, drought_world, epoch
        )

    drought_left = regional_biomass(producers, x_lt=split)
    drought_right = regional_biomass(producers, x_ge=split)

    recovery_world = _force_climate(
        world_state,
        precipitation_left=2.4,
        precipitation_right=1.8,
    )
    for offset in range(recovery_ticks):
        epoch = drought_ticks + offset
        matter = evolve_matter(matter, recovery_world, epoch)
        producers, matter = evolve_producers(producers, matter, recovery_world, epoch)
        consumers, producers, matter = evolve_consumers(
            consumers, producers, matter, recovery_world, epoch
        )

    recovered_left = regional_biomass(producers, x_lt=split)
    recovered_right = regional_biomass(producers, x_ge=split)

    return {
        "before_left": before_left,
        "before_right": before_right,
        "drought_left": drought_left,
        "drought_right": drought_right,
        "recovered_left": recovered_left,
        "recovered_right": recovered_right,
        "total_final_biomass": producer_biomass_kg(producers),
    }
