from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank
from hrm_genesis.ecology.plants import PLANT_ELEMENT_FRACTIONS

from .actions import execute_live_sequence
from .learning import update_contextual_expectations, update_expectations
from .memory import empty_memory, remember
from .perception import perceive_local
from .planning import choose_destination
from .regions import POPULATION_IDS, cells_for_population
from .calibration import physiology_profile


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
HUMAN_COMFORT_TEMPERATURE_C = 22.0
HUMAN_THERMAL_TOLERANCE_C = 14.0
HUMAN_FATIGUE_MOVE_GAIN = 0.08
HUMAN_FATIGUE_REST_RECOVERY = 0.04
HUMAN_HEALING_PER_TICK = 0.03
HUMAN_INJURY_DEATH_THRESHOLD = 1.0


def _blank_elements() -> dict[str, float]:
    return {s: 0.0 for s in HUMAN_TRACKED_ELEMENTS}


def _mass(elements: dict[str, float]) -> float:
    return sum(float(v) for v in elements.values())


def _cell_lookup(cells: list[dict]) -> dict[tuple[int, int], dict]:
    return {(int(c["x"]), int(c["y"])): c for c in cells}


def build_human_state(*, width: int, height: int, seed_bank: SeedBank, cognition_enabled: bool = False, actions_enabled: bool = False, multi_population_enabled: bool = False, calibrated: bool = False, ticks_per_year: int = 120) -> dict:
    profile = physiology_profile(calibrated=calibrated, ticks_per_year=ticks_per_year)
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
                "age_ticks": int(profile["maturity_ticks"]) + rng.randrange(0, max(1, ticks_per_year // 12)),
                "energy": float(profile["initial_energy_kcal"]) + rng.uniform(0.0, float(profile["initial_energy_kcal"]) * 0.05),
                "body_elements_kg": _blank_elements(),
                "body_water_kg": 0.0,
                "generation": 0,
                "last_reproduction_epoch": -1000000,
                "fatigue": 0.0,
                "injury": 0.0,
                "core_temperature_c": 37.0,
        "held_material_elements_kg": _blank_elements(),
                "held_material_elements_kg": _blank_elements(),
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
                "contextual_expectations": {},
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
        "cumulative_births": 0,
        "cumulative_deaths": 0,
        "physiology_profile": profile,
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
            member_index = sum(
                1 for seeded in survivors
                if seeded.get("population_id") == human.get("population_id")
            )
            xy = local_ranked[member_index % len(local_ranked)]
        else:
            xy = ranked[index % len(ranked)]
        human["x"], human["y"] = xy
        pcell, mcell = pcells[xy], mcells[xy]

        profile = humans.get("physiology_profile", physiology_profile(calibrated=False, ticks_per_year=120))
        requested_body = float(profile["seed_dry_mass_kg"])
        available_fraction = 1.0
        for symbol, frac in PLANT_ELEMENT_FRACTIONS.items():
            need = requested_body * frac
            if need > 0.0:
                available_fraction = min(
                    available_fraction,
                    float(pcell["plant_elements_kg"][symbol]) / need,
                )
        requested_water = float(profile["water_capacity_kg"])
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


def _eat(human: dict, pcell: dict, profile: dict) -> float:
    available = _food_mass(pcell)
    if available <= 0.0:
        return 0.0
    bite = min(float(profile["bite_cap_kg"]), available)
    fraction = bite / available
    consumed = 0.0
    for symbol in HUMAN_TRACKED_ELEMENTS:
        amount = float(pcell["plant_elements_kg"][symbol]) * fraction
        pcell["plant_elements_kg"][symbol] -= amount
        keep = amount * float(profile["assimilation"])
        human["body_elements_kg"][symbol] += keep
        pcell["detritus_elements_kg"][symbol] += amount - keep
        consumed += amount
    human["energy"] = float(human["energy"]) + consumed * float(profile["food_energy_kcal_per_kg"]) * float(profile["assimilation"])
    return consumed


def _drink(human: dict, mcell: dict, profile: dict) -> float:
    need = max(0.0, float(profile["water_capacity_kg"]) - float(human["body_water_kg"]))
    from_surface = min(float(mcell["surface_water_kg"]), need)
    mcell["surface_water_kg"] -= from_surface
    remaining = need - from_surface
    from_soil = min(float(mcell["soil_water_kg"]), remaining)
    mcell["soil_water_kg"] -= from_soil
    drank = from_surface + from_soil
    human["body_water_kg"] += drank
    return drank


def _offspring(mother: dict, ordinal: int, profile: dict) -> dict:
    body = _blank_elements()
    for symbol in HUMAN_TRACKED_ELEMENTS:
        amount = float(mother["body_elements_kg"][symbol]) * float(profile["offspring_mass_fraction"])
        mother["body_elements_kg"][symbol] -= amount
        body[symbol] = amount
    water = float(mother["body_water_kg"]) * float(profile["offspring_mass_fraction"])
    mother["body_water_kg"] -= water
    return {
        "id": f"human-b{ordinal:08d}",
        "sex": "female" if ordinal % 2 == 0 else "male",
        "x": int(mother["x"]),
        "y": int(mother["y"]),
        "age_ticks": 0,
        "energy": max(4.0, float(profile["initial_energy_kcal"]) * float(profile["offspring_mass_fraction"])),
        "body_elements_kg": body,
        "body_water_kg": water,
        "generation": int(mother["generation"]) + 1,
        "last_reproduction_epoch": -1000000,
        "fatigue": 0.0,
        "injury": 0.0,
        "core_temperature_c": 37.0,
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
                    "contextual_expectations": {},
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


def _structural_protection(world_cell: dict, producer_cell: dict | None = None) -> tuple[float, float]:
    """Return canopy and terrain protection from physical state, not named techniques."""
    producer_cell = producer_cell or {}
    woody_mass = sum(float(v) for v in producer_cell.get("woody_elements_kg", {}).values())
    arranged_mass = sum(
        float(v) for v in producer_cell.get("arranged_material_elements_kg", {}).values()
    )
    canopy = min(0.80, max(0.0, woody_mass / 8.0))
    terrain_cover = min(0.90, max(0.0, float(world_cell.get("terrain_cover", 0.0))))
    arranged_cover = min(0.45, max(0.0, arranged_mass / 2.0 * 0.45))
    return canopy, min(0.95, terrain_cover + arranged_cover)

def _experienced_reward(
    *,
    start_energy: float,
    start_water: float,
    start_injury: float,
    human: dict,
    profile: dict,
) -> float:
    """Reward the body's experienced result, not a named environmental feature."""
    basal = max(1e-9, float(profile["basal_energy_kcal_per_tick"]))
    water_capacity = max(1e-9, float(profile["water_capacity_kg"]))
    energy_delta = float(human["energy"]) - float(start_energy)
    water_fraction_delta = (float(human["body_water_kg"]) - float(start_water)) / water_capacity
    injury_delta = float(human.get("injury", 0.0)) - float(start_injury)
    return (
        energy_delta
        + water_fraction_delta * basal
        - injury_delta * basal * 2.0
    )



def _apply_physiology(
    human: dict,
    world_cell: dict,
    moved: bool,
    profile: dict | None = None,
    producer_cell: dict | None = None,
) -> None:
    """Apply bounded fatigue, thermoregulation cost, injury, and healing."""
    profile = profile or physiology_profile(calibrated=False, ticks_per_year=120)
    ambient = float(world_cell["temperature"])
    canopy, terrain_cover = _structural_protection(world_cell, producer_cell)

    # Canopy primarily reduces hot exposure; cave/overhang terrain moderates
    # both hot and cold extremes toward a stable subsurface-like temperature.
    if ambient > HUMAN_COMFORT_TEMPERATURE_C:
        ambient -= min(9.0, canopy * 9.0)
    if terrain_cover > 0.0:
        moderation = min(0.55, terrain_cover * 0.55)
        ambient = ambient * (1.0 - moderation) + 15.0 * moderation

    thermal_delta = abs(ambient - HUMAN_COMFORT_TEMPERATURE_C)
    excess = max(0.0, thermal_delta - HUMAN_THERMAL_TOLERANCE_C)

    fatigue = float(human.get("fatigue", 0.0))
    if moved:
        fatigue = min(1.0, fatigue + HUMAN_FATIGUE_MOVE_GAIN)
    else:
        fatigue = max(0.0, fatigue - HUMAN_FATIGUE_REST_RECOVERY)

    if excess > 0.0:
        thermal_cost_cap = 300.0 if bool(profile.get("calibrated")) else 0.30
        thermal_cost_rate = 10.0 if bool(profile.get("calibrated")) else 0.01
        human["energy"] = float(human["energy"]) - min(thermal_cost_cap, excess * thermal_cost_rate)
        if ambient > HUMAN_COMFORT_TEMPERATURE_C:
            human["body_water_kg"] = max(
                0.0,
                float(human["body_water_kg"]) - min(
                    0.75 if bool(profile.get("calibrated")) else 0.02,
                    excess * (0.03 if bool(profile.get("calibrated")) else 0.001),
                ),
            )

    injury = float(human.get("injury", 0.0))
    severe_exposure = max(0.0, thermal_delta - 28.0)
    if severe_exposure > 0.0:
        injury = min(1.5, injury + min(0.08, severe_exposure * 0.002))

    can_heal = (
        injury > 0.0
        and float(human["energy"]) > 6.0
        and float(human["body_water_kg"]) > float(profile["water_capacity_kg"]) * 0.35
        and excess <= 8.0
    )
    if can_heal:
        injury = max(0.0, injury - HUMAN_HEALING_PER_TICK)

    human["fatigue"] = fatigue
    human["injury"] = injury
    human["core_temperature_c"] = 37.0 + max(-2.5, min(2.5, (ambient - 22.0) * 0.03))


def evolve_humans(
    human_state: dict,
    producer_state: dict,
    matter_state: dict,
    world_state: dict,
    epoch: int,
    *,
    cognition_enabled: bool = False,
    actions_enabled: bool = False,
) -> tuple[dict, dict, dict]:
    humans = deepcopy(human_state)
    producers = deepcopy(producer_state)
    matter = deepcopy(matter_state)
    pcells = _cell_lookup(producers["cells"])
    mcells = _cell_lookup(matter["cells"])
    remains = _cell_lookup(humans["remains_cells"])
    wcells = _cell_lookup(world_state["cells"])
    profile = humans.get("physiology_profile", physiology_profile(calibrated=False, ticks_per_year=120))

    adults_by_cell: dict[tuple[int, int], set[str]] = {}
    for person in humans["humans"]:
        if int(person["age_ticks"]) >= int(profile["maturity_ticks"]):
            adults_by_cell.setdefault((int(person["x"]), int(person["y"])), set()).add(str(person["sex"]))

    survivors = []
    births = []
    for human in sorted(humans["humans"], key=lambda h: h["id"]):
        origin = (int(human["x"]), int(human["y"]))
        start_energy = float(human["energy"])
        start_water = float(human["body_water_kg"])
        start_injury = float(human.get("injury", 0.0))
        if cognition_enabled:
            perception = perceive_local(
                human,
                producers,
                matter,
                humans["humans"],
                world_state,
            )
            target = choose_destination(human, perception, human["cognition"])
        else:
            perception = None
            target = _move_toward_food(human, producers)
        moved = target != origin
        if moved:
            human["energy"] = float(human["energy"]) - float(profile["move_energy_kcal_per_tick"])
            human["x"], human["y"] = target

        xy = (int(human["x"]), int(human["y"]))
        if actions_enabled and human.get("learned_sequences"):
            sequence = human["learned_sequences"][-1]
            updated_human, updated_cell, trace = execute_live_sequence(
                sequence,
                human,
                pcells[xy],
            )
            human.update(updated_human)
            pcells[xy].update(updated_cell)
            human["last_action_trace"] = trace
        _drink(human, mcells[xy], profile)
        ate = _eat(human, pcells[xy], profile)
        human["energy"] = float(human["energy"]) - float(profile["basal_energy_kcal_per_tick"])
        _apply_physiology(human, wcells[xy], moved, profile, pcells[xy])
        loss = min(float(human["body_water_kg"]), float(profile["water_loss_per_tick_kg"]))
        human["body_water_kg"] -= loss
        matter["water_output_kg"] = float(matter["water_output_kg"]) + loss
        human["age_ticks"] = int(human["age_ticks"]) + 1

        if cognition_enabled and perception is not None:
            reward = _experienced_reward(
                start_energy=start_energy,
                start_water=start_water,
                start_injury=start_injury,
                human=human,
                profile=profile,
            )
            experienced = deepcopy(perception)
            experienced["origin"] = [xy[0], xy[1]]
            cognition = dict(human["cognition"])
            cognition["memory"] = remember(
                cognition.get("memory", empty_memory()),
                experienced,
                epoch,
                reward,
            )
            cognition["expectations"] = update_expectations(
                cognition.get("expectations", {}),
                experienced,
                reward,
            )
            cognition["contextual_expectations"] = update_contextual_expectations(
                cognition.get("contextual_expectations", {}),
                experienced,
                reward,
            )
            cognition["last_reward"] = round(float(reward), 10)
            cognition["uncertainty"] = round(
                max(0.05, float(cognition.get("uncertainty", 1.0)) * 0.97),
                10,
            )
            human["cognition"] = cognition

        body_mass = _mass(human["body_elements_kg"])
        dead = (
            float(human["energy"]) <= 0.0
            or float(human["body_water_kg"]) <= max(1e-6, float(profile["water_capacity_kg"]) * float(profile["min_water_fraction"]))
            or body_mass <= float(profile["min_dry_mass_kg"])
            or float(human.get("injury", 0.0)) >= HUMAN_INJURY_DEATH_THRESHOLD
            or int(human["age_ticks"]) >= int(profile["max_age_ticks"])
        )
        if dead:
            cell = remains[xy]
            for symbol in HUMAN_TRACKED_ELEMENTS:
                cell["elements_kg"][symbol] += float(human["body_elements_kg"][symbol])
                cell["elements_kg"][symbol] += float(
                    human.get("held_material_elements_kg", {}).get(symbol, 0.0)
                )
            cell["water_kg"] += float(human["body_water_kg"])
            humans["cumulative_deaths"] = int(humans.get("cumulative_deaths", 0)) + 1
            continue

        since_birth = epoch - int(human.get("last_reproduction_epoch", -1000000))
        can_reproduce = (
            human["sex"] == "female"
            and {"female", "male"}.issubset(adults_by_cell.get(xy, set()))
            and float(human["energy"]) >= float(profile["reproduction_energy_kcal"])
            and body_mass >= float(profile["seed_dry_mass_kg"]) * 0.9
            and ate > 0.0
            and since_birth >= int(profile["reproduction_cooldown_ticks"])
        )
        if can_reproduce:
            ordinal = int(humans["next_birth_ordinal"])
            humans["next_birth_ordinal"] = ordinal + 1
            child = _offspring(human, ordinal, profile)
            human["energy"] = max(0.0, float(human["energy"]) - float(child["energy"]))
            human["last_reproduction_epoch"] = epoch
            births.append(child)
            humans["cumulative_births"] = int(humans.get("cumulative_births", 0)) + 1

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
        human["fatigue"] = round(max(0.0, min(1.0, float(human.get("fatigue", 0.0)))), 10)
        human["injury"] = round(max(0.0, float(human.get("injury", 0.0))), 10)
        human["core_temperature_c"] = round(float(human.get("core_temperature_c", 37.0)), 10)
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
        for symbol, amount in human.get("held_material_elements_kg", {}).items():
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
