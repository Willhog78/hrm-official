from __future__ import annotations

from copy import deepcopy
import hashlib

from hrm_coordination.seeds import SeedBank
from hrm_genesis.world.grid import neighbors

from .plants import PLANT_ELEMENT_FRACTIONS
from .traits import (
    CONSUMER_TIMEBASE_ELAPSED,
    CONSUMER_TIMEBASE_LEGACY,
    SPECIES,
    TRAIT_REFERENCE_TICKS_PER_YEAR,
    per_tick_amount,
    per_tick_fraction,
    scaled_life_history_ticks,
    scaled_ticks,
    trait_for,
)


# TIMEBASE note. Under "elapsed-time-v1", flows stated per month (basal energy,
# water loss, bite fraction and cap, carcass decomposition) are converted to the
# run's tick length, as life-history durations are. Not converted: costs per
# event (movement energy per cell moved, a failed hunt, an escape), per-event
# learning steps (forage_bias), hunt success per attempt, and movement speed,
# which stays one cell per tick at any timebase. Speed and per-tick attempt
# frequency therefore still differ between timebases; changing them would need
# fractional movement and is a behaviour change, not a unit conversion.
#
# Per-month (reference tick) rates that are not traits: the bite cap and
# carcass decomposition. Converted to the run's tick length like trait rates.
BITE_CAP_KG_PER_REFERENCE_TICK = 0.004
CARCASS_RETURN_FRACTION_PER_REFERENCE_TICK = 0.05
CARCASS_WATER_RETURN_FRACTION_PER_REFERENCE_TICK = 0.10
# Minimum consecutive supported reference ticks before reproduction.
MIN_SUPPORT_STREAK_REFERENCE_TICKS = 5


def consumer_timebase(consumers: dict) -> str:
    """States without the key predate the timebase correction and replay as
    legacy, so old checkpoints reproduce exactly."""
    return str(consumers.get("rate_timebase", CONSUMER_TIMEBASE_LEGACY))


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
    ticks_per_year: int = 12,
    initial_per_species: int = 2,
    timebase: str = CONSUMER_TIMEBASE_ELAPSED,
) -> dict:
    animals: list[dict] = []
    ordinal = 0
    for species in sorted(SPECIES):
        species_initial = initial_per_species
        if trait_for(species).trophic_role == "predator":
            species_initial = max(1, initial_per_species // 2)
        for local_index in range(species_initial):
            rng = seed_bank.stream(f"ecology.consumer.genesis.{species}.{local_index}")
            maturity_ticks = scaled_life_history_ticks(
                trait_for(species).maturity_ticks,
                ticks_per_year,
            )
            animals.append(
                {
                    "id": f"{species}-g{ordinal:08d}",
                    "species": species,
                    "x": rng.randrange(width),
                    "y": rng.randrange(height),
                    "age_ticks": rng.randrange(0, max(1, maturity_ticks // 2)),
                    "energy": rng.uniform(8.0, 12.0),
                    "body_elements_kg": _blank_elements(),
                    "body_water_kg": rng.uniform(0.08, 0.16),
                    "forage_bias": rng.uniform(-0.05, 0.05),
                    "last_forage_success": 0.0,
                    "support_streak": 0,
                    "generation": 0,
                    "last_reproduction_epoch": -1000000,
                }
            )
            ordinal += 1
    state = {
        "width": width,
        "height": height,
        "ticks_per_year": int(ticks_per_year),
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
    if timebase not in (CONSUMER_TIMEBASE_ELAPSED, CONSUMER_TIMEBASE_LEGACY):
        raise ValueError(f"unknown consumer timebase: {timebase}")
    # Recorded only where it changes behaviour; absent means legacy, and at
    # the reference timebase the two are identical. Earlier states and their
    # ledger digests are therefore unchanged.
    if timebase == CONSUMER_TIMEBASE_ELAPSED and int(ticks_per_year) != TRAIT_REFERENCE_TICKS_PER_YEAR:
        state["rate_timebase"] = timebase
    return state


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
    """Estimate reproductive support from the immediate feeding patch.

    Perception controls movement choice, not carrying-capacity accounting.
    Using perception radius here would perversely punish animals that can see
    farther by charging them for more competitors simply because they detect
    them.
    """
    width, height = int(producers["width"]), int(producers["height"])
    pcells = _cell_lookup(producers["cells"])
    patch = _visible_cells(int(animal["x"]), int(animal["y"]), width, height, 1)
    forage = sum(_plant_mass(pcells[xy]) for xy in patch)
    patch_set = set(patch)
    competitors = sum(
        1
        for other in consumers["animals"]
        if (int(other["x"]), int(other["y"])) in patch_set
    )
    return forage / max(1, competitors)


def _consume_plants(animal: dict, pcell: dict, bite_fraction: float, bite_cap_kg: float) -> float:
    """`bite_fraction` and `bite_cap_kg` are already per tick."""
    traits = trait_for(str(animal["species"]))
    if traits.trophic_role != "herbivore":
        animal["last_forage_success"] = 0.0
        return 0.0
    available = _plant_mass(pcell)
    if available <= 0.0:
        animal["last_forage_success"] = 0.0
        animal["forage_bias"] = max(-0.25, float(animal["forage_bias"]) - 0.01)
        return 0.0

    bite = min(available * bite_fraction, bite_cap_kg)
    fraction = min(1.0, bite / available)
    consumed = 0.0
    assimilated = 0.0
    for symbol in ANIMAL_TRACKED_ELEMENTS:
        amount = float(pcell["plant_elements_kg"][symbol]) * fraction
        pcell["plant_elements_kg"][symbol] -= amount
        retainable = amount * traits.assimilation_efficiency
        target_symbol = traits.adult_body_mass_kg * PLANT_ELEMENT_FRACTIONS[symbol]
        deficit = max(0.0, target_symbol - float(animal["body_elements_kg"][symbol]))
        keep = min(retainable, deficit)
        animal["body_elements_kg"][symbol] += keep
        # Unassimilated food becomes producer detritus in the same cell.
        pcell["detritus_elements_kg"][symbol] += amount - keep
        consumed += amount
        assimilated += keep

    animal["energy"] = min(
        traits.reproduction_energy * 4.0,
        float(animal["energy"]) + consumed * 2200.0 * traits.assimilation_efficiency,
    )
    animal["last_forage_success"] = consumed
    animal["forage_bias"] = min(0.25, float(animal["forage_bias"]) + 0.018)
    return assimilated



def _prey_candidates(predator: dict, consumers: dict) -> list[dict]:
    px, py = int(predator["x"]), int(predator["y"])
    visible = []
    radius = trait_for(str(predator["species"])).perception_radius
    for other in consumers["animals"]:
        if other["id"] == predator["id"]:
            continue
        other_traits = trait_for(str(other["species"]))
        if other_traits.trophic_role == "predator":
            continue
        distance = abs(int(other["x"]) - px) + abs(int(other["y"]) - py)
        if distance <= radius:
            visible.append(other)
    return visible


def _choose_prey(predator: dict, consumers: dict) -> dict | None:
    candidates = _prey_candidates(predator, consumers)
    if not candidates:
        return None

    def score(prey: dict) -> tuple[float, float, str]:
        distance = abs(int(prey["x"]) - int(predator["x"])) + abs(int(prey["y"]) - int(predator["y"]))
        species_bias = 1.0 if prey["species"] == "browser" else 0.75
        body_mass = _element_mass(prey["body_elements_kg"])
        vulnerability = 1.0 / max(0.01, float(prey["energy"]))
        return (species_bias * body_mass - distance * 0.01 + vulnerability * 0.02, -distance, str(prey["id"]))

    return max(candidates, key=score)



def _hunt_succeeds(predator: dict, prey: dict, epoch: int) -> bool:
    species_chance = 0.42 if str(prey["species"]) == "browser" else 0.30
    vulnerability = max(0.0, min(0.20, (8.0 - float(prey["energy"])) * 0.02))
    chance = min(0.75, species_chance + vulnerability)
    raw = hashlib.sha256(
        f"{predator['id']}|{prey['id']}|hunt|{epoch}".encode("utf-8")
    ).digest()
    u = int.from_bytes(raw[:8], "big") / float(2**64 - 1)
    return u < chance


def _carcass_target(carcass_cell: dict) -> dict:
    """Newly dead tissue enters the fresh pool when that pool is modeled."""
    return carcass_cell["fresh_elements_kg"] if "fresh_elements_kg" in carcass_cell else carcass_cell["elements_kg"]


def _consume_prey(predator: dict, prey: dict, carcass_cell: dict) -> float:
    traits = trait_for(str(predator["species"]))
    prey_mass = _element_mass(prey["body_elements_kg"])
    if prey_mass <= 0.0:
        return 0.0

    retained_total = 0.0
    for symbol in ANIMAL_TRACKED_ELEMENTS:
        amount = float(prey["body_elements_kg"][symbol])
        target_symbol = traits.adult_body_mass_kg * PLANT_ELEMENT_FRACTIONS[symbol]
        deficit = max(0.0, target_symbol - float(predator["body_elements_kg"][symbol]))
        retainable = amount * traits.assimilation_efficiency
        keep = min(retainable, deficit)
        predator["body_elements_kg"][symbol] += keep
        _carcass_target(carcass_cell)[symbol] += amount - keep
        retained_total += keep
        prey["body_elements_kg"][symbol] = 0.0

    carcass_cell["water_kg"] += float(prey["body_water_kg"])
    prey["body_water_kg"] = 0.0
    predator["energy"] = min(
        traits.reproduction_energy * 4.0,
        float(predator["energy"]) + prey_mass * 2200.0 * traits.assimilation_efficiency,
    )
    predator["last_forage_success"] = prey_mass
    return prey_mass


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
        "support_streak": 0,
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

    timebase = consumer_timebase(consumers)
    births: list[dict] = []
    survivors: list[dict] = []
    deaths_by_cause = {"old_age": 0, "starvation": 0, "dehydration": 0, "predation": 0}
    killed_ids: set[str] = set()

    for animal in sorted(consumers["animals"], key=lambda a: a["id"]):
        traits = trait_for(str(animal["species"]))
        ticks_per_year = int(consumers.get("ticks_per_year", 12))
        maturity_ticks = scaled_life_history_ticks(traits.maturity_ticks, ticks_per_year)
        max_age_ticks = scaled_life_history_ticks(traits.max_age_ticks, ticks_per_year)
        reproduction_cooldown_ticks = scaled_life_history_ticks(
            traits.reproduction_cooldown_ticks,
            ticks_per_year,
        )
        basal_cost = per_tick_amount(traits.basal_cost, ticks_per_year, timebase)
        water_loss_per_tick = per_tick_amount(traits.water_loss_per_tick_kg, ticks_per_year, timebase)
        origin = (int(animal["x"]), int(animal["y"]))
        if str(animal["id"]) in killed_ids:
            continue

        predator_hungry = (
            traits.trophic_role == "predator"
            and float(animal["energy"]) < traits.reproduction_energy * 0.60
        )
        if predator_hungry:
            prey = _choose_prey(animal, consumers)
            if prey is not None:
                target = (int(prey["x"]), int(prey["y"]))
            else:
                target = _choose_destination(animal, producers, matter)
        else:
            target = _choose_destination(animal, producers, matter)

        step = _move_one_step(origin, target)
        if step != origin:
            animal["energy"] = float(animal["energy"]) - traits.movement_cost
            animal["x"], animal["y"] = step

        xy = (int(animal["x"]), int(animal["y"]))
        pcell = pcells[xy]
        mcell = mcells[xy]

        _drink(animal, mcell)
        if traits.trophic_role == "predator" and predator_hungry:
            prey_here = [
                other for other in consumers["animals"]
                if str(other["id"]) not in killed_ids
                and str(other["id"]) != str(animal["id"])
                and trait_for(str(other["species"])).trophic_role != "predator"
                and (int(other["x"]), int(other["y"])) == xy
            ]
            if prey_here:
                prey = _choose_prey(animal, {"animals": prey_here}) or prey_here[0]
                if _hunt_succeeds(animal, prey, epoch):
                    _consume_prey(animal, prey, carcasses[xy])
                    killed_ids.add(str(prey["id"]))
                    deaths_by_cause["predation"] += 1
                else:
                    animal["energy"] = float(animal["energy"]) - traits.movement_cost * 0.75
                    animal["last_forage_success"] = 0.0
            else:
                animal["last_forage_success"] = 0.0
        else:
            _consume_plants(
                animal, pcell,
                per_tick_fraction(traits.bite_fraction, ticks_per_year, timebase),
                per_tick_amount(BITE_CAP_KG_PER_REFERENCE_TICK, ticks_per_year, timebase),
            )

        animal["energy"] = float(animal["energy"]) - basal_cost
        water_before_loss = max(0.0, float(animal["body_water_kg"]))
        water_loss = min(water_before_loss, water_loss_per_tick)
        animal["body_water_kg"] = water_before_loss - water_loss
        matter["water_output_kg"] = float(matter["water_output_kg"]) + water_loss
        animal["age_ticks"] = int(animal["age_ticks"]) + 1

        body_mass = _element_mass(animal["body_elements_kg"])
        dehydrated = float(animal["body_water_kg"]) <= 1e-6
        starved = float(animal["energy"]) <= 0.0 or body_mass <= 0.002
        old = int(animal["age_ticks"]) >= max_age_ticks

        if dehydrated or starved or old:
            if dehydrated:
                deaths_by_cause["dehydration"] += 1
            elif starved:
                deaths_by_cause["starvation"] += 1
            elif old:
                deaths_by_cause["old_age"] += 1
            ccell = carcasses[xy]
            target = _carcass_target(ccell)
            for symbol in ANIMAL_TRACKED_ELEMENTS:
                target[symbol] += float(animal["body_elements_kg"][symbol])
            ccell["water_kg"] += float(animal["body_water_kg"])
            continue

        if traits.trophic_role == "herbivore":
            local_forage_per_consumer = _local_forage_per_consumer(animal, consumers, producers)
            # Basal cost per tick times cooldown ticks is the energy needed over
            # the cooldown, independent of timebase once basal cost is per tick.
            # Movement is one cell per tick at any timebase (see TIMEBASE note).
            expected_tick_cost = basal_cost + 0.25 * traits.movement_cost
            required_forage_support = (
                expected_tick_cost
                * reproduction_cooldown_ticks
                * 4.0
                / (2200.0 * traits.assimilation_efficiency)
            )
            support_now = (
                float(animal["last_forage_success"]) > 0.0
                and local_forage_per_consumer >= required_forage_support
            )
        else:
            local_prey = len(_prey_candidates(animal, consumers))
            support_now = float(animal["last_forage_success"]) > 0.0 and local_prey >= 1

        animal["support_streak"] = (
            int(animal.get("support_streak", 0)) + 1 if support_now else 0
        )
        since_reproduction = epoch - int(animal.get("last_reproduction_epoch", -1000000))
        reproduction_ready = (
            int(animal["age_ticks"]) >= maturity_ticks
            and float(animal["energy"]) >= traits.reproduction_energy
            and body_mass >= traits.adult_body_mass_kg * 0.45
            and int(animal["support_streak"]) >= max(
                scaled_ticks(MIN_SUPPORT_STREAK_REFERENCE_TICKS, ticks_per_year, timebase),
                reproduction_cooldown_ticks // 3,
            )
            and since_reproduction >= reproduction_cooldown_ticks
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

    consumers["animals"] = [
        animal for animal in survivors
        if str(animal["id"]) not in killed_ids
    ] + births
    consumers["last_tick_births"] = len(births)
    consumers["last_tick_deaths_by_cause"] = deaths_by_cause
    consumers["cumulative_births"] = int(consumers.get("cumulative_births", 0)) + len(births)
    cumulative_deaths = dict(consumers.get("cumulative_deaths_by_cause", {}))
    for cause, count in deaths_by_cause.items():
        cumulative_deaths[cause] = int(cumulative_deaths.get(cause, 0)) + int(count)
    consumers["cumulative_deaths_by_cause"] = cumulative_deaths

    # Carcass decomposition returns consumer material to environmental Matter.
    wcells = _cell_lookup(world_state["cells"]) if world_state.get("cells") else {}
    year_ticks = int(consumers.get("ticks_per_year", 12))
    carcass_return = per_tick_fraction(CARCASS_RETURN_FRACTION_PER_REFERENCE_TICK, year_ticks, timebase)
    carcass_water_return = per_tick_fraction(CARCASS_WATER_RETURN_FRACTION_PER_REFERENCE_TICK, year_ticks, timebase)
    for xy, ccell in carcasses.items():
        mcell = mcells[xy]
        for symbol in ANIMAL_TRACKED_ELEMENTS:
            returned = float(ccell["elements_kg"][symbol]) * carcass_return
            ccell["elements_kg"][symbol] -= returned
            mcell["elements_kg"][symbol] = float(mcell["elements_kg"].get(symbol, 0.0)) + returned
        if "fresh_elements_kg" in ccell:
            spoil = spoilage_fraction(
                float(wcells.get(xy, {}).get("temperature", 20.0)),
                int(consumers.get("ticks_per_year", 12)),
            )
            for symbol in ANIMAL_TRACKED_ELEMENTS:
                fresh = float(ccell["fresh_elements_kg"][symbol])
                # Fresh tissue decomposes at the same rate as other carcass
                # matter, so total carcass decay is unchanged by the split.
                returned = fresh * carcass_return
                spoiled = (fresh - returned) * spoil
                ccell["fresh_elements_kg"][symbol] = fresh - returned - spoiled
                ccell["elements_kg"][symbol] += spoiled
                mcell["elements_kg"][symbol] = float(mcell["elements_kg"].get(symbol, 0.0)) + returned
        water_return = float(ccell["water_kg"]) * carcass_water_return
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
        if "fresh_elements_kg" in ccell:
            ccell["fresh_elements_kg"] = {
                s: round(max(0.0, float(v)), 10)
                for s, v in sorted(ccell["fresh_elements_kg"].items())
            }

    return consumers, producers, matter


# ---------------------------------------------------------------------------
# Fresh tissue and interactions initiated by other organisms (G10.3).

FRESH_SPOILAGE_PER_DAY_COLD = 0.10
FRESH_SPOILAGE_PER_DAY_WARM = 0.55


def spoilage_fraction(temperature_c: float, ticks_per_year: int) -> float:
    """Fraction of fresh tissue that becomes decayed per tick.

    Cold slows spoilage; warmth speeds it. Rates are per day and converted to
    the run's tick length.
    """
    warmth = max(0.0, min(1.0, (float(temperature_c) - 4.0) / 26.0))
    per_day = FRESH_SPOILAGE_PER_DAY_COLD + (FRESH_SPOILAGE_PER_DAY_WARM - FRESH_SPOILAGE_PER_DAY_COLD) * warmth
    days_per_tick = 365.0 / max(1, int(ticks_per_year))
    return 1.0 - (1.0 - per_day) ** days_per_tick


def enable_fresh_tissue(consumer_state: dict) -> dict:
    """Opt-in split of carcass tissue into fresh and decayed pools."""
    consumers = deepcopy(consumer_state)
    for ccell in consumers["carcass_cells"]:
        ccell.setdefault("fresh_elements_kg", _blank_elements())
    return consumers


def kill_animal(consumers: dict, animal_id: str, cause: str) -> dict | None:
    """Remove a living animal exactly once; its whole body becomes fresh carcass
    tissue and carcass water at its cell. Returns the removed animal or None."""
    for index, animal in enumerate(consumers["animals"]):
        if str(animal["id"]) == str(animal_id):
            break
    else:
        return None
    animal = consumers["animals"].pop(index)
    xy = (int(animal["x"]), int(animal["y"]))
    ccell = _cell_lookup(consumers["carcass_cells"])[xy]
    target = _carcass_target(ccell)
    for symbol in ANIMAL_TRACKED_ELEMENTS:
        target[symbol] = float(target.get(symbol, 0.0)) + float(animal["body_elements_kg"][symbol])
    ccell["water_kg"] = float(ccell["water_kg"]) + float(animal["body_water_kg"])
    counts = dict(consumers.get("cumulative_deaths_by_cause", {}))
    counts[cause] = int(counts.get(cause, 0)) + 1
    consumers["cumulative_deaths_by_cause"] = counts
    return animal


def displace_animal(consumers: dict, animal_id: str, draw: float) -> tuple[int, int] | None:
    """An escaping animal flees one cell; it pays its own movement cost."""
    width, height = int(consumers["width"]), int(consumers["height"])
    for animal in consumers["animals"]:
        if str(animal["id"]) != str(animal_id):
            continue
        options = neighbors(int(animal["x"]), int(animal["y"]), width, height)
        if not options:
            return None
        target = options[int(draw * len(options)) % len(options)]
        animal["x"], animal["y"] = target
        animal["energy"] = float(animal["energy"]) - trait_for(str(animal["species"])).movement_cost
        return target
    return None


def consumer_element_totals(state: dict) -> dict[str, float]:
    totals = _blank_elements()
    for animal in state["animals"]:
        for symbol, amount in animal["body_elements_kg"].items():
            totals[symbol] += float(amount)
    for cell in state["carcass_cells"]:
        for symbol, amount in cell["elements_kg"].items():
            totals[symbol] += float(amount)
        for symbol, amount in cell.get("fresh_elements_kg", {}).items():
            totals[symbol] += float(amount)
    return {s: round(v, 10) for s, v in sorted(totals.items())}


def consumer_water_total_kg(state: dict) -> float:
    return (
        sum(float(a["body_water_kg"]) for a in state["animals"])
        + sum(float(c["water_kg"]) for c in state["carcass_cells"])
    )
