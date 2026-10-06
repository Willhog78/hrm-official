from __future__ import annotations

from copy import deepcopy
import hashlib

from hrm_coordination.seeds import SeedBank
from hrm_genesis.world.grid import neighbors

from .plants import PLANT_ELEMENT_FRACTIONS
from .traits import SPECIES, trait_for


ANIMAL_TRACKED_ELEMENTS = tuple(sorted(PLANT_ELEMENT_FRACTIONS))


def _blank_elements() -> dict[str, float]:
    return {symbol: 0.0 for symbol in ANIMAL_TRACKED_ELEMENTS}


def _element_mass(elements: dict[str, float]) -> float:
    return sum(float(v) for v in elements.values())


def _cell_lookup(cells: list[dict]) -> dict[tuple[int, int], dict]:
    return {(int(c["x"]), int(c["y"])): c for c in cells}


def _animal_id(seed: str, species: str, ordinal: int) -> str:
    raw = hashlib.sha256(f"{seed}|{species}|{ordinal}".encode("utf-8")).hexdigest()[:16]
    return f"{species}-{raw}"


def build_consumer_state(
    *,
    width: int,
    height: int,
    seed_bank: SeedBank,
    initial_per_species: int = 2,
) -> dict:
    animals: list[dict] = []
    ordinal = 0
    for species in sorted(SPECIES):
        for local_index in range(initial_per_species):
            rng = seed_bank.stream(f"ecology.consumer.genesis.{species}.{local_index}")
            animals.append(
                {
                    "id": f"{species}-g{ordinal:08d}",
                    "species": species,
                    "x": rng.randrange(width),
                    "y": rng.randrange(height),
                    "age_ticks": rng.randrange(0, max(1, trait_for(species).maturity_ticks // 2)),
                    "energy": rng.uniform(8.0, 12.0),
                    "body_elements_kg": _blank_elements(),
                    "body_water_kg": rng.uniform(0.08, 0.16),
                    "forage_bias": rng.uniform(-0.05, 0.05),
                    "last_forage_success": 0.0,
                    "generation": 0,
                    "last_reproduction_epoch": -1000000,
                }
            )
            ordinal += 1
    return {
        "width": width,
        "height": height,
        "epoch_applied": -1,
        "next_birth_ordinal": ordinal,
        "cumulative_births": 0,
        "cumulative_deaths_by_cause": {"old_age": 0, "starvation": 0, "dehydration": 0},
        "animals": animals,
        "carcass_cells": [
            {"x": x, "y": y, "elements_kg": _blank_elements(), "water_kg": 0.0}
            for y in range(height)
            for x in range(width)
        ],
    }


def seed_initial_consumers(
    consumer_state: dict,
    producer_state: dict,
    matter_state: dict,
) -> tuple[dict, dict, dict]:
    """Pay for initial animal bodies out of producer biomass and Matter water."""
    consumers = deepcopy(consumer_state)
    producers = deepcopy(producer_state)
    matter = deepcopy(matter_state)
    pcells = _cell_lookup(producers["cells"])
    mcells = _cell_lookup(matter["cells"])

    vegetated = sorted(
        pcells,
        key=lambda xy: (-_plant_mass(pcells[xy]), xy[1], xy[0]),
    )
    if not vegetated or _plant_mass(pcells[vegetated[0]]) <= 0.0:
        consumers["animals"] = []
        return consumers, producers, matter

    survivors: list[dict] = []
    for index, animal in enumerate(consumers["animals"]):
        xy = vegetated[index % len(vegetated)]
        animal["x"], animal["y"] = xy
        pcell = pcells[xy]
        mcell = mcells[xy]

        requested_body = 0.012
        available_fraction = 1.0
        for symbol in ANIMAL_TRACKED_ELEMENTS:
            needed = requested_body * PLANT_ELEMENT_FRACTIONS[symbol]
            available = float(pcell["plant_elements_kg"][symbol])
            if needed > 0:
                available_fraction = min(available_fraction, available / needed)

        requested_water = float(animal["body_water_kg"])
        if requested_water > 0:
            available_fraction = min(
                available_fraction,
                (float(mcell["soil_water_kg"]) + float(mcell["surface_water_kg"])) / requested_water,
            )

        fraction = max(0.0, min(1.0, available_fraction))
        if fraction < 0.35:
            continue

        body_mass = requested_body * fraction
        for symbol in ANIMAL_TRACKED_ELEMENTS:
            amount = body_mass * PLANT_ELEMENT_FRACTIONS[symbol]
            pcell["plant_elements_kg"][symbol] -= amount
            animal["body_elements_kg"][symbol] = amount

        water = requested_water * fraction
        take_soil = min(float(mcell["soil_water_kg"]), water)
        mcell["soil_water_kg"] -= take_soil
        remaining = water - take_soil
        mcell["surface_water_kg"] -= min(float(mcell["surface_water_kg"]), remaining)
        animal["body_water_kg"] = water
        survivors.append(animal)

    consumers["animals"] = survivors
    return consumers, producers, matter


def _visible_cells(x: int, y: int, width: int, height: int, radius: int) -> tuple[tuple[int, int], ...]:
    cells = []
    for yy in range(max(0, y - radius), min(height, y + radius + 1)):
        for xx in range(max(0, x - radius), min(width, x + radius + 1)):
            if abs(xx - x) + abs(yy - y) <= radius:
                cells.append((xx, yy))
    return tuple(sorted(cells))


def _plant_mass(cell: dict) -> float:
    return sum(float(v) for v in cell["plant_elements_kg"].values())


def _water_available(cell: dict) -> float:
    return float(cell["surface_water_kg"]) + float(cell["soil_water_kg"])


def _choose_destination(animal: dict, producers: dict, matter: dict) -> tuple[int, int]:
    width, height = int(producers["width"]), int(producers["height"])
    pcells = _cell_lookup(producers["cells"])
    mcells = _cell_lookup(matter["cells"])
    traits = trait_for(str(animal["species"]))
    origin = (int(animal["x"]), int(animal["y"]))
    visible = _visible_cells(origin[0], origin[1], width, height, traits.perception_radius)

    hunger = max(0.0, 8.0 - float(animal["energy"]))
    thirst = max(0.0, traits.water_capacity_kg * 0.5 - float(animal["body_water_kg"]))
    learned = float(animal["forage_bias"])

    def score(xy: tuple[int, int]) -> tuple[float, int, int]:
        food = _plant_mass(pcells[xy])
        water = _water_available(mcells[xy])
        distance = abs(xy[0] - origin[0]) + abs(xy[1] - origin[1])
        value = food * (1.0 + 0.08 * hunger + learned) + water * 0.002 * (1.0 + thirst * 8.0)
        value -= distance * traits.movement_cost * 0.45
        return (value, -distance, -(xy[1] * width + xy[0]))

    return max(visible, key=score)


def _move_one_step(origin: tuple[int, int], target: tuple[int, int]) -> tuple[int, int]:
    if origin == target:
        return origin
    candidates = neighbors(origin[0], origin[1], max(origin[0], target[0]) + 2, max(origin[1], target[1]) + 2)
    # Avoid depending on the helper's artificial bounds for far-edge cases.
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    if abs(dx) >= abs(dy) and dx != 0:
        return (origin[0] + (1 if dx > 0 else -1), origin[1])
    if dy != 0:
        return (origin[0], origin[1] + (1 if dy > 0 else -1))
    return origin


def _local_forage_per_consumer(animal: dict, consumers: dict, producers: dict) -> float:
    width, height = int(producers["width"]), int(producers["height"])
    pcells = _cell_lookup(producers["cells"])
    traits = trait_for(str(animal["species"]))
    visible = _visible_cells(int(animal["x"]), int(animal["y"]), width, height, traits.perception_radius)
    forage = sum(_plant_mass(pcells[xy]) for xy in visible)
    competitors = 0
    visible_set = set(visible)
    for other in consumers["animals"]:
        if (int(other["x"]), int(other["y"])) in visible_set:
            competitors += 1
    return forage / max(1, competitors)


def _consume_plants(animal: dict, pcell: dict) -> float:
    traits = trait_for(str(animal["species"]))
    available = _plant_mass(pcell)
    if available <= 0.0:
        animal["last_forage_success"] = 0.0
        animal["forage_bias"] = max(-0.25, float(animal["forage_bias"]) - 0.01)
        return 0.0

    bite = min(available * traits.bite_fraction, 0.004)
    fraction = min(1.0, bite / available)
    consumed = 0.0
    assimilated = 0.0
    for symbol in ANIMAL_TRACKED_ELEMENTS:
        amount = float(pcell["plant_elements_kg"][symbol]) * fraction
        pcell["plant_elements_kg"][symbol] -= amount
        keep = amount * traits.assimilation_efficiency
        animal["body_elements_kg"][symbol] += keep
        # Unassimilated food becomes producer detritus in the same cell.
        pcell["detritus_elements_kg"][symbol] += amount - keep
        consumed += amount
        assimilated += keep

    animal["energy"] = float(animal["energy"]) + consumed * 2200.0 * traits.assimilation_efficiency
    animal["last_forage_success"] = consumed
    animal["forage_bias"] = min(0.25, float(animal["forage_bias"]) + 0.018)
    return assimilated


def _drink(animal: dict, mcell: dict) -> float:
    traits = trait_for(str(animal["species"]))
    need = max(0.0, traits.water_capacity_kg - float(animal["body_water_kg"]))
    if need <= 0.0:
        return 0.0
    from_surface = min(float(mcell["surface_water_kg"]), need)
    mcell["surface_water_kg"] -= from_surface
    remaining = need - from_surface
    from_soil = min(float(mcell["soil_water_kg"]), remaining)
    mcell["soil_water_kg"] -= from_soil
    drank = from_surface + from_soil
    animal["body_water_kg"] += drank
    return drank


def _offspring(parent: dict, ordinal: int) -> dict:
    species = str(parent["species"])
    traits = trait_for(species)
    child_elements = _blank_elements()
    for symbol in ANIMAL_TRACKED_ELEMENTS:
        amount = float(parent["body_elements_kg"][symbol]) * traits.offspring_mass_fraction
        parent["body_elements_kg"][symbol] -= amount
        child_elements[symbol] = amount
    child_water = float(parent["body_water_kg"]) * traits.offspring_mass_fraction
    parent["body_water_kg"] -= child_water

    # Heritable variation is deterministic from parent/ordinal, bounded and small.
    raw = hashlib.sha256(f"{parent['id']}|{ordinal}".encode("utf-8")).digest()
    delta = (int.from_bytes(raw[:2], "big") / 65535.0 - 0.5) * 0.04

    return {
        "id": f"{species}-b{ordinal:08d}",
        "species": species,
        "x": int(parent["x"]),
        "y": int(parent["y"]),
        "age_ticks": 0,
        "energy": max(3.0, float(parent["energy"]) * 0.18),
        "body_elements_kg": child_elements,
        "body_water_kg": child_water,
        "forage_bias": max(-0.25, min(0.25, float(parent["forage_bias"]) + delta)),
        "last_forage_success": 0.0,
        "generation": int(parent["generation"]) + 1,
        "last_reproduction_epoch": -1000000,
    }


def evolve_consumers(
    consumer_state: dict,
    producer_state: dict,
    matter_state: dict,
    world_state: dict,
    epoch: int,
) -> tuple[dict, dict, dict]:
    consumers = deepcopy(consumer_state)
    producers = deepcopy(producer_state)
    matter = deepcopy(matter_state)

    pcells = _cell_lookup(producers["cells"])
    mcells = _cell_lookup(matter["cells"])
    carcasses = _cell_lookup(consumers["carcass_cells"])

    births: list[dict] = []
    survivors: list[dict] = []
    deaths_by_cause = {"old_age": 0, "starvation": 0, "dehydration": 0}

    for animal in sorted(consumers["animals"], key=lambda a: a["id"]):
        traits = trait_for(str(animal["species"]))
        origin = (int(animal["x"]), int(animal["y"]))
        target = _choose_destination(animal, producers, matter)
        step = _move_one_step(origin, target)

        if step != origin:
            animal["energy"] = float(animal["energy"]) - traits.movement_cost
            animal["x"], animal["y"] = step

        xy = (int(animal["x"]), int(animal["y"]))
        pcell = pcells[xy]
        mcell = mcells[xy]

        _drink(animal, mcell)
        _consume_plants(animal, pcell)

        animal["energy"] = float(animal["energy"]) - traits.basal_cost
        water_before_loss = max(0.0, float(animal["body_water_kg"]))
        water_loss = min(water_before_loss, traits.water_loss_per_tick_kg)
        animal["body_water_kg"] = water_before_loss - water_loss
        matter["water_output_kg"] = float(matter["water_output_kg"]) + water_loss
        animal["age_ticks"] = int(animal["age_ticks"]) + 1

        body_mass = _element_mass(animal["body_elements_kg"])
        dehydrated = float(animal["body_water_kg"]) <= 1e-6
        starved = float(animal["energy"]) <= 0.0 or body_mass <= 0.002
        old = int(animal["age_ticks"]) >= traits.max_age_ticks

        if dehydrated or starved or old:
            if dehydrated:
                deaths_by_cause["dehydration"] += 1
            elif starved:
                deaths_by_cause["starvation"] += 1
            elif old:
                deaths_by_cause["old_age"] += 1
            ccell = carcasses[xy]
            for symbol in ANIMAL_TRACKED_ELEMENTS:
                ccell["elements_kg"][symbol] += float(animal["body_elements_kg"][symbol])
            ccell["water_kg"] += float(animal["body_water_kg"])
            continue

        local_forage_per_consumer = _local_forage_per_consumer(animal, consumers, producers)
        expected_tick_cost = traits.basal_cost + 0.25 * traits.movement_cost
        required_forage_support = (
            expected_tick_cost
            * traits.reproduction_cooldown_ticks
            * 2.0
            / (2200.0 * traits.assimilation_efficiency)
        )
        since_reproduction = epoch - int(animal.get("last_reproduction_epoch", -1000000))
        reproduction_ready = (
            int(animal["age_ticks"]) >= traits.maturity_ticks
            and float(animal["energy"]) >= traits.reproduction_energy
            and body_mass >= 0.015
            and float(animal["last_forage_success"]) > 0.0
            and local_forage_per_consumer >= required_forage_support
            and since_reproduction >= traits.reproduction_cooldown_ticks
        )
        if reproduction_ready:
            ordinal = int(consumers["next_birth_ordinal"])
            consumers["next_birth_ordinal"] = ordinal + 1
            child = _offspring(animal, ordinal)
            child_energy = float(child["energy"])
            animal["energy"] = max(0.0, float(animal["energy"]) - child_energy)
            animal["last_reproduction_epoch"] = epoch
            births.append(child)

        survivors.append(animal)

    consumers["animals"] = survivors + births
    consumers["last_tick_births"] = len(births)
    consumers["last_tick_deaths_by_cause"] = deaths_by_cause
    consumers["cumulative_births"] = int(consumers.get("cumulative_births", 0)) + len(births)
    cumulative_deaths = dict(consumers.get("cumulative_deaths_by_cause", {}))
    for cause, count in deaths_by_cause.items():
        cumulative_deaths[cause] = int(cumulative_deaths.get(cause, 0)) + int(count)
    consumers["cumulative_deaths_by_cause"] = cumulative_deaths

    # Carcass decomposition returns consumer material to environmental Matter.
    for xy, ccell in carcasses.items():
        mcell = mcells[xy]
        for symbol in ANIMAL_TRACKED_ELEMENTS:
            returned = float(ccell["elements_kg"][symbol]) * 0.05
            ccell["elements_kg"][symbol] -= returned
            mcell["elements_kg"][symbol] = float(mcell["elements_kg"].get(symbol, 0.0)) + returned
        water_return = float(ccell["water_kg"]) * 0.10
        ccell["water_kg"] -= water_return
        mcell["soil_water_kg"] += water_return

    consumers["epoch_applied"] = epoch

    for animal in consumers["animals"]:
        animal["energy"] = round(float(animal["energy"]), 10)
        animal["body_water_kg"] = round(max(0.0, float(animal["body_water_kg"])), 10)
        animal["forage_bias"] = round(float(animal["forage_bias"]), 10)
        animal["last_forage_success"] = round(float(animal["last_forage_success"]), 10)
        animal["body_elements_kg"] = {
            s: round(max(0.0, float(v)), 10)
            for s, v in sorted(animal["body_elements_kg"].items())
        }
    for ccell in consumers["carcass_cells"]:
        ccell["water_kg"] = round(max(0.0, float(ccell["water_kg"])), 10)
        ccell["elements_kg"] = {
            s: round(max(0.0, float(v)), 10)
            for s, v in sorted(ccell["elements_kg"].items())
        }

    return consumers, producers, matter


def consumer_element_totals(state: dict) -> dict[str, float]:
    totals = _blank_elements()
    for animal in state["animals"]:
        for symbol, amount in animal["body_elements_kg"].items():
            totals[symbol] += float(amount)
    for cell in state["carcass_cells"]:
        for symbol, amount in cell["elements_kg"].items():
            totals[symbol] += float(amount)
    return {s: round(v, 10) for s, v in sorted(totals.items())}


def consumer_water_total_kg(state: dict) -> float:
    return (
        sum(float(a["body_water_kg"]) for a in state["animals"])
        + sum(float(c["water_kg"]) for c in state["carcass_cells"])
    )
