from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank
from hrm_genesis.world.grid import neighbors


# Tracked dry-matter fractions. These are a deliberately reduced biological
# accounting basis for G2, not a claim that untracked plant chemistry vanishes.
# Growth can occur only by moving these tracked elements out of Matter.
PLANT_ELEMENT_FRACTIONS: dict[str, float] = {
    "C": 0.860,
    "N": 0.080,
    "K": 0.025,
    "P": 0.012,
    "Mg": 0.013,
    "S": 0.010,
}

GERMINATION_SEED_MASS_KG = 0.002
BASE_GROWTH_FRACTION = 0.055
WATER_KG_PER_KG_GROWTH = 2.5
BASE_MORTALITY_FRACTION = 0.004
MAX_AGE_TICKS = 360
REPRODUCTION_FRACTION = 0.012
DECOMPOSITION_FRACTION = 0.035


def _blank_elements() -> dict[str, float]:
    return {symbol: 0.0 for symbol in PLANT_ELEMENT_FRACTIONS}


def _mass(elements: dict[str, float]) -> float:
    return sum(float(v) for v in elements.values())


def _live_mass(cell: dict) -> float:
    return _mass(cell["plant_elements_kg"]) + _mass(cell.get("woody_elements_kg", {}))




def _burnable_mass(cell: dict) -> float:
    return (
        _mass(cell.get("woody_elements_kg", {}))
        + _mass(cell.get("loose_material_elements_kg", {}))
        + _mass(cell.get("arranged_material_elements_kg", {}))
    )


def _burn_fraction(source: dict[str, float], fraction: float) -> dict[str, float]:
    burned = {}
    for symbol, raw in source.items():
        amount = max(0.0, float(raw) * fraction)
        source[symbol] = float(raw) - amount
        burned[symbol] = amount
    return burned


def _cell_lookup(cells: list[dict]) -> dict[tuple[int, int], dict]:
    return {(int(c["x"]), int(c["y"])): c for c in cells}


def build_producer_state(*, width: int, height: int) -> dict:
    return {
        "width": width,
        "height": height,
        "epoch_applied": -1,
        "cells": [
            {
                "x": x,
                "y": y,
                "plant_elements_kg": _blank_elements(),
                "woody_elements_kg": _blank_elements(),
                "loose_material_elements_kg": _blank_elements(),
                "arranged_material_elements_kg": _blank_elements(),
                "arrangement_geometry": {
                    "span_m": 0.0,
                    "height_m": 0.0,
                    "density": 0.0,
                    "surface_area_m2": 0.0,
                },
                "fire_intensity": 0.0,
                "seed_elements_kg": _blank_elements(),
                "detritus_elements_kg": _blank_elements(),
                "age_ticks": 0,
            }
            for y in range(height)
            for x in range(width)
        ],
    }


def seed_initial_producers(
    matter_state: dict,
    producer_state: dict,
    seed_bank: SeedBank,
    biomass_scale_factor: float = 1.0,
) -> tuple[dict, dict]:
    """Move real Matter inventory into sparse initial producer biomass.

    Initial life is part of Genesis initial conditions, not created on tick 1.
    Every seeded gram is debited from Matter before replay genesis is registered.
    """
    matter = deepcopy(matter_state)
    ecology = deepcopy(producer_state)
    matter_lookup = _cell_lookup(matter["cells"])
    ecology_lookup = _cell_lookup(ecology["cells"])

    for xy, pcell in ecology_lookup.items():
        rng = seed_bank.stream(f"ecology.producer.genesis.{xy[0]}.{xy[1]}")
        # Sparse colonization: no target population is maintained later.
        if rng.random() > 0.55:
            continue
        requested_mass = rng.uniform(0.03, 0.12) * biomass_scale_factor
        mcell = matter_lookup[xy]

        limit = requested_mass
        for symbol, frac in PLANT_ELEMENT_FRACTIONS.items():
            available = float(mcell["elements_kg"].get(symbol, 0.0))
            if frac > 0:
                limit = min(limit, available / frac)
        biomass = max(0.0, limit)
        if biomass <= 0.0:
            continue

        for symbol, frac in PLANT_ELEMENT_FRACTIONS.items():
            amount = biomass * frac
            mcell["elements_kg"][symbol] -= amount
            pcell["plant_elements_kg"][symbol] += amount

    return matter, ecology


def _environment_factors(world_cell: dict, matter_cell: dict) -> tuple[float, float, float]:
    solar = max(0.0, float(world_cell["solar"]))
    temp = float(world_cell["temperature"])
    water = max(0.0, float(matter_cell["soil_water_kg"]))

    light_factor = min(1.0, solar / 0.85)
    temp_factor = max(0.0, 1.0 - abs(temp - 22.0) / 24.0)
    water_factor = min(1.0, water / 18.0)
    return light_factor, temp_factor, water_factor


def _growth_limit(matter_cell: dict, desired_growth: float) -> float:
    allowed = max(0.0, desired_growth)
    for symbol, frac in PLANT_ELEMENT_FRACTIONS.items():
        available = max(0.0, float(matter_cell["elements_kg"].get(symbol, 0.0)))
        allowed = min(allowed, available / frac)
    water = max(0.0, float(matter_cell["soil_water_kg"]))
    allowed = min(allowed, water / WATER_KG_PER_KG_GROWTH)
    return max(0.0, allowed)


def _transfer_fraction(source: dict[str, float], fraction: float) -> dict[str, float]:
    moved: dict[str, float] = {}
    for symbol in PLANT_ELEMENT_FRACTIONS:
        amount = max(0.0, float(source[symbol]) * fraction)
        source[symbol] -= amount
        moved[symbol] = amount
    return moved


def evolve_producers(
    producer_state: dict,
    matter_state: dict,
    world_state: dict,
    epoch: int,
) -> tuple[dict, dict]:
    ecology = deepcopy(producer_state)
    matter = deepcopy(matter_state)

    width = int(ecology["width"])
    height = int(ecology["height"])
    pcells = _cell_lookup(ecology["cells"])
    mcells = _cell_lookup(matter["cells"])
    wcells = _cell_lookup(world_state["cells"])
    for pcell in pcells.values():
        pcell.setdefault("woody_elements_kg", _blank_elements())
        pcell.setdefault("loose_material_elements_kg", _blank_elements())
        pcell.setdefault("arranged_material_elements_kg", _blank_elements())
        pcell.setdefault(
            "arrangement_geometry",
            {"span_m": 0.0, "height_m": 0.0, "density": 0.0, "surface_area_m2": 0.0},
        )
        pcell.setdefault("fire_intensity", 0.0)

    # 1. Decomposition returns previously dead material to Matter.
    for xy, pcell in pcells.items():
        mcell = mcells[xy]
        for symbol in PLANT_ELEMENT_FRACTIONS:
            pool = float(pcell["detritus_elements_kg"][symbol])
            returned = pool * DECOMPOSITION_FRACTION
            pcell["detritus_elements_kg"][symbol] -= returned
            mcell["elements_kg"][symbol] = float(mcell["elements_kg"].get(symbol, 0.0)) + returned

    # 2. Germination converts seed material into living material when the local
    # environment is viable. No material is created.
    for xy, pcell in pcells.items():
        light, temp, water = _environment_factors(wcells[xy], mcells[xy])
        seed_mass = _mass(pcell["seed_elements_kg"])
        if seed_mass >= GERMINATION_SEED_MASS_KG and min(light, temp, water) > 0.28:
            fraction = min(1.0, GERMINATION_SEED_MASS_KG / seed_mass)
            established = _live_mass(pcell)
            moved = _transfer_fraction(pcell["seed_elements_kg"], fraction)
            for symbol, amount in moved.items():
                pcell["plant_elements_kg"][symbol] += amount
            # Cell age is the biomass-weighted age of its vegetation: seedlings
            # enter at age 0 without rejuvenating established plants.
            total = _live_mass(pcell)
            if total > 0.0:
                pcell["age_ticks"] = int(round(int(pcell["age_ticks"]) * established / total))

    # 3. Existing biomass grows by consuming Matter pools and water.
    for xy, pcell in pcells.items():
        live_mass = _live_mass(pcell)
        if live_mass <= 0.0:
            continue

        light, temp, water = _environment_factors(wcells[xy], mcells[xy])
        condition = min(light, temp, water)
        desired = max(0.0, live_mass * BASE_GROWTH_FRACTION * condition)
        growth = _growth_limit(mcells[xy], desired)

        if growth > 0.0:
            woody_share = 0.0
            if int(pcell["age_ticks"]) >= 30 and condition >= 0.60:
                # Woody structure emerges only under sustained viable growth
                # conditions; it is not randomly assigned to cells.
                woody_share = min(0.55, 0.15 + (condition - 0.60) * 0.80)
            for symbol, frac in PLANT_ELEMENT_FRACTIONS.items():
                amount = growth * frac
                mcells[xy]["elements_kg"][symbol] -= amount
                pcell["plant_elements_kg"][symbol] += amount * (1.0 - woody_share)
                pcell["woody_elements_kg"][symbol] += amount * woody_share

            water_used = growth * WATER_KG_PER_KG_GROWTH
            mcells[xy]["soil_water_kg"] -= water_used
            # G2 does not model atmospheric vapor as a retained reservoir, so
            # transpiration is an explicit open-system water output.
            matter["water_output_kg"] = float(matter["water_output_kg"]) + water_used

        pcell["age_ticks"] = int(pcell["age_ticks"]) + 1


    # 3b. Natural combustion: ignition comes from the physical world, not humans.
    # Existing fire can persist/spread locally while dry combustible material exists.
    ignition_additions: dict[tuple[int, int], float] = {xy: 0.0 for xy in pcells}
    for xy, pcell in pcells.items():
        wcell = wcells[xy]
        fuel = _burnable_mass(pcell)
        moisture = max(0.0, min(1.0, float(wcell.get("precipitation", 0.0)) / 5.0))
        lightning = max(0.0, float(wcell.get("lightning", 0.0)))
        current = max(0.0, float(pcell.get("fire_intensity", 0.0)))
        if fuel > 0.05 and lightning > 0.0 and moisture < 0.6:
            current = max(current, min(1.0, 0.25 + 0.75 * lightning))
        if current > 0.0 and fuel > 0.0:
            burn_fraction = min(0.22, current * 0.08 + 0.01)
            for bucket in ("woody_elements_kg", "loose_material_elements_kg", "arranged_material_elements_kg"):
                burned = _burn_fraction(pcell[bucket], burn_fraction)
                for symbol, amount in burned.items():
                    pcell["detritus_elements_kg"][symbol] += amount
            fuel_after = _burnable_mass(pcell)
            rain_quench = min(0.85, float(wcell.get("precipitation", 0.0)) / 6.0)
            current = max(0.0, current * (0.82 - 0.55 * rain_quench))
            if fuel_after < 0.02:
                current = 0.0
            if current > 0.18:
                for other in neighbors(xy[0], xy[1], width, height):
                    if _burnable_mass(pcells[other]) > 0.05:
                        ignition_additions[other] = max(
                            ignition_additions[other], min(0.35, current * 0.18)
                        )
        pcell["fire_intensity"] = current

    for xy, addition in ignition_additions.items():
        if addition > 0.0:
            pcells[xy]["fire_intensity"] = max(float(pcells[xy]["fire_intensity"]), addition)

    # 4. Mortality is condition- and age-sensitive. Dead matter stays in the
    # ecology authority as detritus until decomposition returns it.
    for xy, pcell in pcells.items():
        live_mass = _live_mass(pcell)
        if live_mass <= 0.0:
            continue
        light, temp, water = _environment_factors(wcells[xy], mcells[xy])
        stress = 1.0 - min(light, temp, water)
        old_age = max(0.0, (int(pcell["age_ticks"]) - MAX_AGE_TICKS) / MAX_AGE_TICKS)
        mortality = min(0.85, BASE_MORTALITY_FRACTION + 0.08 * stress + 0.12 * old_age)
        dead = _transfer_fraction(pcell["plant_elements_kg"], mortality)
        woody_dead = _transfer_fraction(pcell["woody_elements_kg"], mortality * 0.35)
        for symbol, amount in dead.items():
            pcell["detritus_elements_kg"][symbol] += amount
        for symbol, amount in woody_dead.items():
            pcell["detritus_elements_kg"][symbol] += amount
        if _live_mass(pcell) <= 1e-12:
            pcell["age_ticks"] = 0

    # 5. Reproduction transfers a small fraction of living biomass into seeds
    # and disperses it. Seed production therefore has a real material cost.
    seed_additions = {xy: _blank_elements() for xy in pcells}
    for xy, pcell in pcells.items():
        live_mass = _mass(pcell["plant_elements_kg"])
        if live_mass < 0.02:
            continue
        light, temp, water = _environment_factors(wcells[xy], mcells[xy])
        if min(light, temp, water) < 0.5:
            continue

        seed = _transfer_fraction(pcell["plant_elements_kg"], REPRODUCTION_FRACTION)
        destinations = (xy,) + neighbors(xy[0], xy[1], width, height)
        share_count = len(destinations)
        for destination in destinations:
            for symbol, amount in seed.items():
                seed_additions[destination][symbol] += amount / share_count

    for xy, additions in seed_additions.items():
        for symbol, amount in additions.items():
            pcells[xy]["seed_elements_kg"][symbol] += amount

    ecology["epoch_applied"] = epoch
    for pcell in ecology["cells"]:
        pcell["fire_intensity"] = round(max(0.0, min(1.0, float(pcell.get("fire_intensity", 0.0)))), 10)
    matter["epoch_applied"] = epoch

    for pcell in ecology["cells"]:
        for bucket in (
            "plant_elements_kg",
            "woody_elements_kg",
            "loose_material_elements_kg",
            "arranged_material_elements_kg",
            "seed_elements_kg",
            "detritus_elements_kg",
        ):
            pcell[bucket] = {
                symbol: round(max(0.0, float(amount)), 10)
                for symbol, amount in sorted(pcell[bucket].items())
            }
    for mcell in matter["cells"]:
        mcell["soil_water_kg"] = round(max(0.0, float(mcell["soil_water_kg"])), 10)
        mcell["surface_water_kg"] = round(max(0.0, float(mcell["surface_water_kg"])), 10)
        mcell["elements_kg"] = {
            symbol: round(max(0.0, float(amount)), 10)
            for symbol, amount in sorted(mcell["elements_kg"].items())
        }
    matter["water_output_kg"] = round(float(matter["water_output_kg"]), 10)
    return ecology, matter


def producer_biomass_kg(state: dict) -> float:
    return sum(_live_mass(c) for c in state["cells"])


def producer_edible_biomass_kg(state: dict) -> float:
    return sum(_mass(c["plant_elements_kg"]) for c in state["cells"])


def producer_woody_biomass_kg(state: dict) -> float:
    return sum(_mass(c.get("woody_elements_kg", {})) for c in state["cells"])


def producer_seed_mass_kg(state: dict) -> float:
    return sum(_mass(c["seed_elements_kg"]) for c in state["cells"])


def producer_detritus_mass_kg(state: dict) -> float:
    return sum(_mass(c["detritus_elements_kg"]) for c in state["cells"])


def ecology_element_totals(state: dict) -> dict[str, float]:
    totals = _blank_elements()
    for cell in state["cells"]:
        for bucket in (
            "plant_elements_kg",
            "woody_elements_kg",
            "loose_material_elements_kg",
            "arranged_material_elements_kg",
            "seed_elements_kg",
            "detritus_elements_kg",
        ):
            for symbol, amount in cell.get(bucket, {}).items():
                totals[symbol] += float(amount)
    return {symbol: round(value, 10) for symbol, value in sorted(totals.items())}
