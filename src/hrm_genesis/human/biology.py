from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank
from hrm_genesis.ecology.plants import PLANT_ELEMENT_FRACTIONS

from .learning import update_expectations
from .memory import empty_memory, remember
from .perception import perceive_local
from .planning import choose_destination
from .regions import POPULATION_IDS, cells_for_population


HUMAN_TRACKED_ELEMENTS = tuple(sorted(PLANT_ELEMENT_FRACTIONS))
HUMAN_BASAL_COST = 0.42
HUMAN_MOVE_COST = 0.18
HUMAN_WATER_CAPACITY_KG = 0.85
HUMAN_WATER_LOSS_PER_TICK_KG = 0.06
HUMAN_BITE_CAP_KG = 0.018
HUMAN_ASSIMILATION = 0.72
HUMAN_MATURITY_TICKS = 180
HUMAN_MAX_AGE_TICKS = 900
HUMAN_REPRODUCTION_ENERGY = 18.0
HUMAN_REPRODUCTION_COOLDOWN = 60
HUMAN_OFFSPRING_MASS_FRACTION = 0.12


def _blank_elements() -> dict[str, float]:
    return {s: 0.0 for s in HUMAN_TRACKED_ELEMENTS}


def _mass(elements: dict[str, float]) -> float:
    return sum(float(v) for v in elements.values())


def _cell_lookup(cells: list[dict]) -> dict[tuple[int, int], dict]:
    return {(int(c["x"]), int(c["y"])): c for c in cells}


def build_human_state(*, width: int, height: int, seed_bank: SeedBank, cognition_enabled: bool = False, actions_enabled: bool = False, multi_population_enabled: bool = False) -> dict:
    humans = []
    founders = []
    if multi_population_enabled:
        for population_id in POPULATION_IDS:
            founders.extend(((population_id, "female"), (population_id, "male")))
    else:
        founders = [(None, "female"), (None, "male")]

    for index, (population_id, sex) in enumerate(founders):
        rng = seed_bank.stream(f"human.genesis.{index}")
        person = {
                "id": f"human-g{index:08d}",
                "sex": sex,
                "x": rng.randrange(width),
                "y": rng.randrange(height),
                "age_ticks": HUMAN_MATURITY_TICKS + rng.randrange(0, 24),
                "energy": 14.0 + rng.uniform(0.0, 2.0),
                "body_elements_kg": _blank_elements(),
                "body_water_kg": 0.0,
                "generation": 0,
                "last_reproduction_epoch": -1000000,
            }
        if population_id is not None:
            region_cells = cells_for_population(population_id, width, height)
            start_xy = region_cells[index % len(region_cells)]
            person["x"], person["y"] = start_xy
            person["population_id"] = population_id
            person["home_region"] = population_id
        if cognition_enabled:
            person["cognition"] = {
                "memory": empty_memory(),
                "expectations": {},
                "uncertainty": 1.0,
                "last_reward": 0.0,
            }
        if actions_enabled:
            person["learned_sequences"] = []
            person["last_teacher_id"] = None
        humans.append(person)
    return {
        "width": width,
        "height": height,
        "epoch_applied": -1,
        "next_birth_ordinal": len(humans),
        "humans": humans,
        "remains_cells": [
            {"x": x, "y": y, "elements_kg": _blank_elements(), "water_kg": 0.0}
            for y in range(height)
            for x in range(width)
        ],
    }


def seed_initial_humans(human_state: dict, producer_state: dict, matter_state: dict) -> tuple[dict, dict, dict]:
    """Pay for initial human bodies from existing producer biomass and water.

    Genesis seeding is intentionally small relative to real adult anatomy so G5
    can qualify material pathways without inventing a second food substrate.
    """
    humans = deepcopy(human_state)
    producers = deepcopy(producer_state)
    matter = deepcopy(matter_state)
    pcells = _cell_lookup(producers["cells"])
    mcells = _cell_lookup(matter["cells"])

    ranked = sorted(pcells, key=lambda xy: (-_mass(pcells[xy]["plant_elements_kg"]), xy[1], xy[0]))
    survivors = []
    for index, human in enumerate(humans["humans"]):
        if not ranked:
            break
        if "population_id" in human:
            local = [
                xy for xy in cells_for_population(
                    str(human["population_id"]),
                    int(producers["width"]),
                    int(producers["height"]),
                )
                if _mass(pcells[xy]["plant_elements_kg"]) > 0.0
            ]
            local_ranked = sorted(local, key=lambda xy: (-_mass(pcells[xy]["plant_elements_kg"]), xy[1], xy[0]))
            if not local_ranked:
                continue
            xy = local_ranked[index % len(local_ranked)]
        else:
            xy = ranked[index % len(ranked)]
        human["x"], human["y"] = xy
        pcell, mcell = pcells[xy], mcells[xy]

        requested_body = 0.08
        available_fraction = 1.0
        for symbol, frac in PLANT_ELEMENT_FRACTIONS.items():
            need = requested_body * frac
            if need > 0.0:
                available_fraction = min(
                    available_fraction,
                    float(pcell["plant_elements_kg"][symbol]) / need,
                )
        requested_water = 0.55
        available_water = float(mcell["surface_water_kg"]) + float(mcell["soil_water_kg"])
        available_fraction = min(available_fraction, available_water / requested_water)
        fraction = max(0.0, min(1.0, available_fraction))
        if fraction < 0.5:
            continue

        for symbol, frac in PLANT_ELEMENT_FRACTIONS.items():
            amount = requested_body * fraction * frac
            pcell["plant_elements_kg"][symbol] -= amount
            human["body_elements_kg"][symbol] = amount

        water = requested_water * fraction
        surface = min(float(mcell["surface_water_kg"]), water)
        mcell["surface_water_kg"] -= surface
        soil = min(float(mcell["soil_water_kg"]), water - surface)
        mcell["soil_water_kg"] -= soil
        human["body_water_kg"] = surface + soil
        survivors.append(human)

    humans["humans"] = survivors
    return humans, producers, matter


def _food_mass(pcell: dict) -> float:
    return _mass(pcell["plant_elements_kg"])


def _move_toward_food(human: dict, producers: dict) -> tuple[int, int]:
    width, height = int(producers["width"]), int(producers["height"])
    pcells = _cell_lookup(producers["cells"])
    x, y = int(human["x"]), int(human["y"])
    candidates = [(x, y)]
    if x > 0:
        candidates.append((x - 1, y))
    if x + 1 < width:
        candidates.append((x + 1, y))
    if y > 0:
        candidates.append((x, y - 1))
    if y + 1 < height:
        candidates.append((x, y + 1))
    return max(candidates, key=lambda xy: (_food_mass(pcells[xy]), -xy[1], -xy[0]))


def _eat(human: dict, pcell: dict) -> float:
    available = _food_mass(pcell)
    if available <= 0.0:
        return 0.0
    bite = min(HUMAN_BITE_CAP_KG, available)
    fraction = bite / available
    consumed = 0.0
    for symbol in HUMAN_TRACKED_ELEMENTS:
        amount = float(pcell["plant_elements_kg"][symbol]) * fraction
        pcell["plant_elements_kg"][symbol] -= amount
        keep = amount * HUMAN_ASSIMILATION
        human["body_elements_kg"][symbol] += keep
        pcell["detritus_elements_kg"][symbol] += amount - keep
        consumed += amount
    human["energy"] = float(human["energy"]) + consumed * 2200.0 * HUMAN_ASSIMILATION
    return consumed


def _drink(human: dict, mcell: dict) -> float:
    need = max(0.0, HUMAN_WATER_CAPACITY_KG - float(human["body_water_kg"]))
    from_surface = min(float(mcell["surface_water_kg"]), need)
    mcell["surface_water_kg"] -= from_surface
    remaining = need - from_surface
    from_soil = min(float(mcell["soil_water_kg"]), remaining)
    mcell["soil_water_kg"] -= from_soil
    drank = from_surface + from_soil
    human["body_water_kg"] += drank
    return drank


def _offspring(mother: dict, ordinal: int) -> dict:
    body = _blank_elements()
    for symbol in HUMAN_TRACKED_ELEMENTS:
        amount = float(mother["body_elements_kg"][symbol]) * HUMAN_OFFSPRING_MASS_FRACTION
        mother["body_elements_kg"][symbol] -= amount
        body[symbol] = amount
    water = float(mother["body_water_kg"]) * HUMAN_OFFSPRING_MASS_FRACTION
    mother["body_water_kg"] -= water
    return {
        "id": f"human-b{ordinal:08d}",
        "sex": "female" if ordinal % 2 == 0 else "male",
        "x": int(mother["x"]),
        "y": int(mother["y"]),
        "age_ticks": 0,
        "energy": 4.0,
        "body_elements_kg": body,
        "body_water_kg": water,
        "generation": int(mother["generation"]) + 1,
        "last_reproduction_epoch": -1000000,
        **(
            {
                "population_id": mother["population_id"],
                "home_region": mother.get("home_region", mother["population_id"]),
            }
            if "population_id" in mother
            else {}
        ),
        **(
            {
                "cognition": {
                    "memory": empty_memory(),
                    "expectations": {},
                    "uncertainty": 1.0,
                    "last_reward": 0.0,
                }
            }
            if "cognition" in mother
            else {}
        ),
        **(
            {"learned_sequences": [], "last_teacher_id": None}
            if "learned_sequences" in mother
            else {}
        ),
    }


def evolve_humans(
    human_state: dict,
    producer_state: dict,
    matter_state: dict,
    world_state: dict,
    epoch: int,
    *,
    cognition_enabled: bool = False,
) -> tuple[dict, dict, dict]:
    humans = deepcopy(human_state)
    producers = deepcopy(producer_state)
    matter = deepcopy(matter_state)
    pcells = _cell_lookup(producers["cells"])
    mcells = _cell_lookup(matter["cells"])
    remains = _cell_lookup(humans["remains_cells"])

    adults_by_cell: dict[tuple[int, int], set[str]] = {}
    for person in humans["humans"]:
        if int(person["age_ticks"]) >= HUMAN_MATURITY_TICKS:
            adults_by_cell.setdefault((int(person["x"]), int(person["y"])), set()).add(str(person["sex"]))

    survivors = []
    births = []
    for human in sorted(humans["humans"], key=lambda h: h["id"]):
        origin = (int(human["x"]), int(human["y"]))
        if cognition_enabled:
            perception = perceive_local(human, producers, matter, humans["humans"])
            target = choose_destination(human, perception, human["cognition"])
        else:
            perception = None
            target = _move_toward_food(human, producers)
        if target != origin:
            human["energy"] = float(human["energy"]) - HUMAN_MOVE_COST
            human["x"], human["y"] = target

        xy = (int(human["x"]), int(human["y"]))
        _drink(human, mcells[xy])
        ate = _eat(human, pcells[xy])
        if cognition_enabled and perception is not None:
            reward = ate * 2200.0 * HUMAN_ASSIMILATION
            cognition = dict(human["cognition"])
            cognition["memory"] = remember(cognition.get("memory", empty_memory()), perception, epoch, reward)
            cognition["expectations"] = update_expectations(cognition.get("expectations", {}), perception, reward)
            cognition["last_reward"] = round(float(reward), 10)
            cognition["uncertainty"] = round(max(0.05, float(cognition.get("uncertainty", 1.0)) * 0.97), 10)
            human["cognition"] = cognition

        human["energy"] = float(human["energy"]) - HUMAN_BASAL_COST
        loss = min(float(human["body_water_kg"]), HUMAN_WATER_LOSS_PER_TICK_KG)
        human["body_water_kg"] -= loss
        matter["water_output_kg"] = float(matter["water_output_kg"]) + loss
        human["age_ticks"] = int(human["age_ticks"]) + 1

        body_mass = _mass(human["body_elements_kg"])
        dead = (
            float(human["energy"]) <= 0.0
            or float(human["body_water_kg"]) <= 1e-6
            or body_mass <= 0.01
            or int(human["age_ticks"]) >= HUMAN_MAX_AGE_TICKS
        )
        if dead:
            cell = remains[xy]
            for symbol in HUMAN_TRACKED_ELEMENTS:
                cell["elements_kg"][symbol] += float(human["body_elements_kg"][symbol])
            cell["water_kg"] += float(human["body_water_kg"])
            continue

        since_birth = epoch - int(human.get("last_reproduction_epoch", -1000000))
        can_reproduce = (
            human["sex"] == "female"
            and {"female", "male"}.issubset(adults_by_cell.get(xy, set()))
            and float(human["energy"]) >= HUMAN_REPRODUCTION_ENERGY
            and body_mass >= 0.09
            and ate > 0.0
            and since_birth >= HUMAN_REPRODUCTION_COOLDOWN
        )
        if can_reproduce:
            ordinal = int(humans["next_birth_ordinal"])
            humans["next_birth_ordinal"] = ordinal + 1
            child = _offspring(human, ordinal)
            human["energy"] = max(0.0, float(human["energy"]) - float(child["energy"]))
            human["last_reproduction_epoch"] = epoch
            births.append(child)

        survivors.append(human)

    humans["humans"] = survivors + births

    for xy, cell in remains.items():
        mcell = mcells[xy]
        for symbol in HUMAN_TRACKED_ELEMENTS:
            returned = float(cell["elements_kg"][symbol]) * 0.04
            cell["elements_kg"][symbol] -= returned
            mcell["elements_kg"][symbol] = float(mcell["elements_kg"].get(symbol, 0.0)) + returned
        water_return = float(cell["water_kg"]) * 0.08
        cell["water_kg"] -= water_return
        mcell["soil_water_kg"] += water_return

    humans["epoch_applied"] = epoch
    for human in humans["humans"]:
        human["energy"] = round(float(human["energy"]), 10)
        human["body_water_kg"] = round(max(0.0, float(human["body_water_kg"])), 10)
        human["body_elements_kg"] = {
            s: round(max(0.0, float(v)), 10)
            for s, v in sorted(human["body_elements_kg"].items())
        }
    for cell in humans["remains_cells"]:
        cell["water_kg"] = round(max(0.0, float(cell["water_kg"])), 10)
        cell["elements_kg"] = {
            s: round(max(0.0, float(v)), 10)
            for s, v in sorted(cell["elements_kg"].items())
        }
    matter["water_output_kg"] = round(float(matter["water_output_kg"]), 10)
    return humans, producers, matter


def human_element_totals(state: dict) -> dict[str, float]:
    totals = _blank_elements()
    for human in state["humans"]:
        for symbol, amount in human["body_elements_kg"].items():
            totals[symbol] += float(amount)
    for cell in state["remains_cells"]:
        for symbol, amount in cell["elements_kg"].items():
            totals[symbol] += float(amount)
    return {s: round(v, 10) for s, v in sorted(totals.items())}


def human_water_total_kg(state: dict) -> float:
    return (
        sum(float(h["body_water_kg"]) for h in state["humans"])
        + sum(float(c["water_kg"]) for c in state["remains_cells"])
    )
