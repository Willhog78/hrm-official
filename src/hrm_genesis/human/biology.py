from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank
from hrm_genesis.ecology.plants import PLANT_ELEMENT_FRACTIONS
from hrm_genesis.ecology.traits import opportunity_draw, opportunity_probability, trait_for

from .actions import execute_live_sequence
from .diet import FOOD_KINDS, forage_at_cell, ingest_pool, innate_food_prior, pool_for
from . import interactions as cap
from .learning import update_contextual_expectations, update_expectations
from .memory import empty_memory, remember
from .perception import extend_perception_with_materials, perceive_local
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
# G10.6: a night's sleep removes a fraction of the day's fatigue whether or not
# the agent walked, so ordinary daily walking reaches a steady state
# (0.08 x 0.75 / 0.25 = 0.24) instead of saturating. Declared values.
HUMAN_FATIGUE_SLEEP_RECOVERY_MOVED = 0.25
HUMAN_FATIGUE_SLEEP_RECOVERY_RESTED = 0.40
HUMAN_HEALING_PER_TICK = 0.03
HUMAN_INJURY_DEATH_THRESHOLD = 1.0


def _blank_elements() -> dict[str, float]:
    return {s: 0.0 for s in HUMAN_TRACKED_ELEMENTS}


def _mass(elements: dict[str, float]) -> float:
    return sum(float(v) for v in elements.values())


def _cell_lookup(cells: list[dict]) -> dict[tuple[int, int], dict]:
    return {(int(c["x"]), int(c["y"])): c for c in cells}


def build_human_state(*, width: int, height: int, seed_bank: SeedBank, cognition_enabled: bool = False, actions_enabled: bool = False, multi_population_enabled: bool = False, calibrated: bool = False, ticks_per_year: int = 120, physiology_version: str = "reference-v1") -> dict:
    profile = physiology_profile(calibrated=calibrated, ticks_per_year=ticks_per_year, version=physiology_version)
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
        "cumulative_deaths_by_cause": {
            "energy": 0,
            "dehydration": 0,
            "low_body_mass": 0,
            "injury": 0,
            "old_age": 0,
        },
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


def _development_scale(human: dict, profile: dict) -> float:
    """Age-scaled body capacity from birth fraction to adult reference at maturity."""
    if not bool(profile.get("calibrated")):
        return 1.0
    birth = max(0.01, min(1.0, float(profile["offspring_mass_fraction"])))
    maturity = max(1, int(profile["maturity_ticks"]))
    progress = max(0.0, min(1.0, float(human.get("age_ticks", 0)) / maturity))
    return birth + (1.0 - birth) * progress


def _age_profile(human: dict, profile: dict) -> dict:
    if not bool(profile.get("calibrated")):
        return profile
    scale = _development_scale(human, profile)
    adjusted = dict(profile)
    adjusted["development_scale"] = scale
    adjusted["target_dry_mass_kg"] = float(profile["seed_dry_mass_kg"]) * scale
    adjusted["water_capacity_kg"] = float(profile["water_capacity_kg"]) * scale
    adjusted["bite_cap_kg"] = float(profile["bite_cap_kg"]) * max(0.10, scale)
    if "metabolic_scaling_exponent" in profile:
        # reference-v2: maintenance scales with body size^0.75 (Kleiber).
        metabolic = scale ** float(profile["metabolic_scaling_exponent"])
    else:
        metabolic = max(0.10, scale)
    adjusted["adult_basal_energy_kcal_per_tick"] = float(profile["basal_energy_kcal_per_tick"])
    adjusted["basal_energy_kcal_per_tick"] = float(profile["basal_energy_kcal_per_tick"]) * metabolic
    adjusted["move_energy_kcal_per_tick"] = float(profile["move_energy_kcal_per_tick"]) * max(0.10, scale)
    adjusted["water_loss_per_tick_kg"] = float(profile["water_loss_per_tick_kg"]) * metabolic
    adjusted["min_dry_mass_kg"] = float(profile["min_dry_mass_kg"]) * scale
    adjusted["thermal_scale"] = max(0.08, scale)
    dependent_age = int(profile.get("dependent_age_ticks", 0))
    independent_age = max(dependent_age, int(profile.get("independent_feeding_age_ticks", dependent_age)))
    age = int(human.get("age_ticks", 0))
    if dependent_age <= 0 or age >= independent_age:
        dependence = 0.0
    elif age <= dependent_age:
        dependence = 1.0
    else:
        span = max(1, independent_age - dependent_age)
        dependence = max(0.0, 1.0 - (age - dependent_age) / span)
    adjusted["caregiver_dependence"] = dependence
    # Three roles, separated (docs/architecture/CAREGIVING_SOLID_FOOD.md). Each
    # is computed from the same age curve as before, so values are unchanged;
    # each is read only where its role applies.
    adjusted["nursing_factor"] = dependence           # milk energy, water and dry mass
    adjusted["carried"] = dependence > 0.0            # goes with its caregiver
    adjusted["self_feeding"] = 1.0 - dependence       # forages for itself when > 0
    return adjusted


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
    target_dry_mass = float(profile.get("target_dry_mass_kg", profile["seed_dry_mass_kg"]))
    for symbol in HUMAN_TRACKED_ELEMENTS:
        amount = float(pcell["plant_elements_kg"][symbol]) * fraction
        pcell["plant_elements_kg"][symbol] -= amount
        target_symbol = target_dry_mass * float(PLANT_ELEMENT_FRACTIONS[symbol])
        deficit = max(0.0, target_symbol - float(human["body_elements_kg"][symbol]))
        retainable = amount * float(profile["assimilation"])
        keep = min(retainable, deficit)
        human["body_elements_kg"][symbol] += keep
        pcell["detritus_elements_kg"][symbol] += amount - keep
        consumed += amount
    human["energy"] = min(
        float(profile.get("energy_store_capacity_kcal", profile.get("energy_capacity_kcal", float("inf")))),
        float(human["energy"]) + consumed * float(profile["food_energy_kcal_per_kg"]) * float(profile["assimilation"]),
    )
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
        "caregiver_id": str(mother["id"]),
        "last_reproduction_epoch": -1000000,
        "fatigue": 0.0,
        "injury": 0.0,
        "core_temperature_c": 37.0,
        "held_material_elements_kg": _blank_elements(),
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




def _resolve_caregiver(
    child: dict,
    people_by_id: dict[str, dict],
    profile: dict,
) -> dict | None:
    if float(profile.get("caregiver_dependence", 0.0)) <= 0.0:
        return None

    current = people_by_id.get(str(child.get("caregiver_id", "")))
    if current is not None and int(current.get("age_ticks", 0)) >= int(profile.get("maturity_ticks", 0)):
        return current

    cx, cy = int(child["x"]), int(child["y"])
    candidates = []
    for other in people_by_id.values():
        if str(other["id"]) == str(child["id"]):
            continue
        if int(other.get("age_ticks", 0)) < int(profile.get("maturity_ticks", 0)):
            continue
        distance = abs(int(other["x"]) - cx) + abs(int(other["y"]) - cy)
        if distance <= 1:
            candidates.append((distance, str(other["id"]), other))

    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    replacement = candidates[0][2]
    child["caregiver_id"] = str(replacement["id"])
    return replacement


def _provision_dependent(
    child: dict,
    caregiver: dict | None,
    profile: dict,
    nursing_model: str | None = None,
    stats: dict | None = None,
) -> float:
    dependence = max(0.0, min(1.0, float(profile.get("nursing_factor", profile.get("caregiver_dependence", 0.0)))))
    if caregiver is None or dependence <= 0.0:
        return 0.0

    if (int(child["x"]), int(child["y"])) != (int(caregiver["x"]), int(caregiver["y"])):
        return 0.0

    transferred = 0.0
    dry_cap = float(profile.get("nursing_dry_mass_kg_per_tick", 0.0)) * dependence
    target_dry_mass = float(profile.get("target_dry_mass_kg", 0.0))
    child_dry_mass = _mass(child["body_elements_kg"])
    dry_need = max(0.0, target_dry_mass - child_dry_mass)
    dry_transfer = min(dry_cap, dry_need)

    if dry_transfer > 0.0:
        caregiver_mass = max(1e-9, _mass(caregiver["body_elements_kg"]))
        transferable_fraction = min(1.0, dry_transfer / caregiver_mass)
        for symbol in HUMAN_TRACKED_ELEMENTS:
            amount = float(caregiver["body_elements_kg"][symbol]) * transferable_fraction
            caregiver["body_elements_kg"][symbol] -= amount
            child["body_elements_kg"][symbol] += amount
            transferred += amount

    water_need = max(0.0, float(profile["water_capacity_kg"]) - float(child["body_water_kg"]))
    water_cap = float(profile.get("nursing_water_kg_per_tick", 0.0)) * dependence
    caregiver_water_floor = max(0.0, float(caregiver["body_water_kg"]) * 0.55)
    water_available = max(0.0, float(caregiver["body_water_kg"]) - caregiver_water_floor)
    water = min(water_need, water_cap, water_available)
    caregiver["body_water_kg"] -= water
    child["body_water_kg"] += water

    energy_cap = float(profile.get("nursing_energy_kcal_per_tick", 0.0)) * dependence
    child_capacity = float(profile.get(
        "energy_store_capacity_kcal",
        float(profile.get("energy_capacity_kcal", float("inf"))) * max(0.10, float(profile.get("development_scale", 1.0)))))
    if "lactation_efficiency" in profile:
        # reference-v2: milk is drawn from the mother's own reserve, tapering
        # as that reserve runs low; synthesis costs her 1/efficiency per kcal.
        efficiency = float(profile["lactation_efficiency"])
        reserve_reference = float(profile["energy_capacity_kcal"]) * float(profile["lactation_taper_reserve_fraction"])
        taper = max(0.0, min(1.0, float(caregiver["energy"]) / max(1e-9, reserve_reference)))
        mother_floor = float(profile.get("adult_basal_energy_kcal_per_tick", profile["basal_energy_kcal_per_tick"]))
        energy_available = max(0.0, float(caregiver["energy"]) - mother_floor) * efficiency
        supply = min(energy_cap * taper, energy_available)
    else:
        # reference-v1 states no conversion loss: one kcal of milk costs one.
        efficiency = 1.0
        caregiver_energy_floor = max(0.0, float(profile.get("basal_energy_kcal_per_tick", 0.0)))
        energy_available = max(0.0, float(caregiver["energy"]) - caregiver_energy_floor)
        supply = min(energy_cap, energy_available)
    if nursing_model == NURSING_DEMAND_LIMITED:
        # docs/architecture/DEMAND_LIMITED_MILK.md: what the child can receive
        # (room in its store) is fixed before any milk is made; the mother
        # makes only that and pays for it, conversion loss included.
        room = max(0.0, child_capacity - float(child["energy"]))
        energy = min(supply, room)
    else:
        energy = supply
    cost = energy / efficiency
    caregiver["energy"] -= cost
    before = float(child["energy"])
    child["energy"] = min(child_capacity, before + energy)
    if stats is not None:
        absorbed = float(child["energy"]) - before
        stats["nursing_days"] = int(stats.get("nursing_days", 0)) + 1
        for key, value in (
            ("milk_supply_kcal", supply),                  # what the supply cap would have drawn
            ("milk_produced_kcal", energy),                # made and handed over
            ("milk_cost_kcal", cost),                      # charged to the mother
            ("milk_conversion_heat_kcal", cost - energy),  # synthesis loss, lost as heat
            ("milk_absorbed_kcal", max(0.0, absorbed)),
            # Produced but not taken into the child's store. Zero by construction
            # when demand-limited; recorded so any gap is visible, not erased.
            ("milk_unabsorbed_kcal", max(0.0, energy - max(0.0, absorbed))),
            # Pre-existing: a child already above its size-scaled store (from
            # food) is cut back to it. Not milk; kept visible.
            ("child_store_clamp_kcal", max(0.0, before - float(child["energy"]))),
        ):
            stats[key] = float(stats.get(key, 0.0)) + value
        if energy < supply:
            stats["nursing_days_demand_limited"] = int(stats.get("nursing_days_demand_limited", 0)) + 1
    return transferred + water


ENERGY_STORE_SIZE_SCALED = "size-scaled-v1"
ENERGY_STORE_LEGACY = "unscaled-eating-legacy"


def energy_store_capacity(profile: dict) -> float:
    """The one energy store bound for eating, hand-feeding and nursing: the
    adult capacity scaled by body development (adults: scale 1, unchanged)."""
    return float(profile.get("energy_capacity_kcal", float("inf"))) * max(0.10, float(profile.get("development_scale", 1.0)))


def _record_refused(stats: dict, profile: dict, kcal: float) -> None:
    """Energy offered by food that a full store could not take, by age class.
    The food mass is eaten as before; only its surplus energy is refused."""
    if kcal <= 0.0:
        return
    key = "child" if float(profile.get("development_scale", 1.0)) < 1.0 else "adult"
    refused = dict(stats.get("refused_kcal", {}))
    refused[key] = float(refused.get(key, 0.0)) + kcal
    stats["refused_kcal"] = refused


NURSING_DEMAND_LIMITED = "demand-limited-v1"
NURSING_SUPPLY_CAPPED_LEGACY = "supply-capped-legacy"


# Complementary (solid) food can be given from this age. Declared biological
# reference: in humans complementary feeding begins at about six months. It is
# not a weaning age; milk is unchanged.
SOLID_FOOD_ONSET_DAYS = 180
CHILD_HUNGER_RESERVE = 0.75  # the planner's own hunger threshold, as a visible cue


def _provision_solid_food(
    child: dict,
    caregiver: dict | None,
    child_profile: dict,
    caregiver_profile: dict,
    pcell: dict,
    ccell: dict | None,
    eaten_kg: float,
    stats: dict,
    store_stats: dict | None = None,
) -> float:
    """A caregiver hands food it obtains from the shared cell to its dependent
    child (caregiving_model "solid-food-v1"). The caregiver's hands hold
    exactly what it took; the child ingests from the hands with its own
    capacity, assimilation and hazard; what is not eaten goes back to the cell
    the same day. The caregiver pays handling at adult scale. Returns kg eaten.
    """
    def outcome(name: str) -> float:
        counts = dict(stats.get("solid_food_outcomes", {}))
        counts[name] = int(counts.get(name, 0)) + 1
        stats["solid_food_outcomes"] = counts
        return 0.0

    if float(child_profile.get("nursing_factor", 0.0)) <= 0.0:
        return 0.0
    if caregiver is None:
        return outcome("no_caregiver")
    if int(child.get("age_ticks", 0)) < SOLID_FOOD_ONSET_DAYS:
        return outcome("too_young")
    if (int(caregiver["x"]), int(caregiver["y"])) != (int(child["x"]), int(child["y"])):
        return outcome("not_together")
    reference = float(child_profile.get("satiety_reference_kcal", child_profile.get("energy_capacity_kcal", 1.0)))
    reference *= max(0.10, float(child_profile.get("development_scale", 1.0)))
    if float(child["energy"]) / max(1e-9, reference) >= CHILD_HUNGER_RESERVE:
        return outcome("not_hungry")
    room = float(child_profile["bite_cap_kg"]) - max(0.0, float(eaten_kg))
    if room <= 1e-12:
        return outcome("gut_full")
    known = caregiver.get("cognition", {}).get("food_values", {})
    kinds = sorted((k for k, v in known.items() if float(v) > 0.0 and k in FOOD_KINDS),
                   key=lambda k: (-float(known[k]), list(FOOD_KINDS).index(k)))
    adult_scale = max(0.10, float(caregiver_profile.get("development_scale", 1.0)))
    eaten = 0.0
    for kind in kinds:
        if room <= 1e-12:
            break
        pool = pool_for(kind, pcell, ccell)
        available = 0.0 if pool is None else sum(float(v) for v in pool.values())
        if available <= 0.0:
            continue
        spec = FOOD_KINDS[kind]
        reach = float("inf") if spec["hand_access_kg"] is None else float(spec["hand_access_kg"]) * adult_scale
        take = min(room, available, reach)
        if take <= 0.0:
            continue
        # Obtain: mass moves from the cell into the caregiver's hands.
        fraction = take / available
        hands = {}
        for symbol in sorted(pool):
            amount = float(pool[symbol]) * fraction
            pool[symbol] = float(pool[symbol]) - amount
            hands[symbol] = amount
        caregiver["energy"] = float(caregiver["energy"]) - take * float(spec["handling_kcal_per_kg"]) * adult_scale
        # Hand over: the child eats from the hands; the rest goes back.
        rec = ingest_pool(child, kind, take, hands, pcell["detritus_elements_kg"], child_profile, pay_handling=False)
        if store_stats is not None:
            _record_refused(store_stats, child_profile, float(rec.get("refused_kcal", 0.0)))
        for symbol, amount in hands.items():
            pool[symbol] = float(pool[symbol]) + amount
        if rec["kg"] > 0.0:
            room -= rec["kg"]
            eaten += rec["kg"]
            kg = dict(stats.get("solid_food_kg_by_kind", {}))
            kg[kind] = float(kg.get(kind, 0.0)) + rec["kg"]
            stats["solid_food_kg_by_kind"] = kg
            stats["solid_food_kcal"] = float(stats.get("solid_food_kcal", 0.0)) + rec["kcal"]
            stats["solid_food_handling_kcal"] = float(stats.get("solid_food_handling_kcal", 0.0)) + take * float(spec["handling_kcal_per_kg"]) * adult_scale
    if eaten <= 0.0:
        return outcome("no_known_food_here")
    outcome("fed")
    return eaten


def _structural_protection(world_cell: dict, producer_cell: dict | None = None) -> tuple[float, float]:
    """Return canopy and terrain protection from physical state, not named techniques."""
    producer_cell = producer_cell or {}
    woody_mass = sum(float(v) for v in producer_cell.get("woody_elements_kg", {}).values())
    arranged_mass = sum(
        float(v) for v in producer_cell.get("arranged_material_elements_kg", {}).values()
    )
    geometry = producer_cell.get("arrangement_geometry", {})
    span = max(0.0, float(geometry.get("span_m", 0.0)))
    height = max(0.0, float(geometry.get("height_m", 0.0)))
    density = max(0.0, min(1.0, float(geometry.get("density", 0.0))))
    area = max(0.0, float(geometry.get("surface_area_m2", 0.0)))
    canopy = min(0.80, max(0.0, woody_mass / 8.0))
    terrain_cover = min(0.90, max(0.0, float(world_cell.get("terrain_cover", 0.0))))
    geometry_factor = min(1.0, (span / 1.5) * (height / 1.2) * density)
    arranged_cover = min(0.45, max(0.0, geometry_factor * min(1.0, area / 2.0) * 0.45))
    if arranged_mass <= 0.0:
        arranged_cover = 0.0
    return canopy, min(0.95, terrain_cover + arranged_cover)

def _add_interoception(perception: dict, human: dict, profile: dict, base_profile: dict) -> None:
    """Thirst and hunger as felt reserves, in days (agentus_thirst_enabled).

    Declared assumption: an organism senses how depleted its water and energy
    are. It does not sense where water is beyond its perception radius; it may
    recall places it has seen.
    """
    capacity = float(profile["water_capacity_kg"])
    loss = max(1e-9, float(profile["water_loss_per_tick_kg"]))
    floor = capacity * float(base_profile["min_water_fraction"])
    body_water = float(human["body_water_kg"])
    perception["water_need_kg"] = max(0.0, capacity - body_water) + loss
    perception["hydration_days"] = max(0.0, (body_water - floor) / loss)
    perception["energy_days"] = max(0.0, float(human["energy"])) / max(1e-9, float(profile["basal_energy_kcal_per_tick"]))
    visible = {(int(c["x"]), int(c["y"])) for c in perception["cells"]}
    perception["remembered_water"] = [
        [int(k.split(",")[0]), int(k.split(",")[1]), float(v.get("water_kg", 0.0)), int(v.get("last_seen_epoch", 0))]
        for k, v in sorted(human.get("cognition", {}).get("memory", {}).get("locations", {}).items())
        if (int(k.split(",")[0]), int(k.split(",")[1])) not in visible
    ]


def _catabolize_lean_tissue(human: dict, profile: dict, detritus: dict) -> float:
    """reference-v2: an empty fat reserve is covered by breaking down lean dry
    tissue. Its tracked elements leave the body as excreta into the cell's
    detritus, so mass is conserved. Returns kg catabolized."""
    deficit = -float(human["energy"])
    per_kg = float(profile["lean_catabolism_kcal_per_kg"])
    mass = _mass(human["body_elements_kg"])
    take = min(mass, deficit / per_kg)
    if take <= 0.0:
        return 0.0
    fraction = take / mass
    for symbol in sorted(human["body_elements_kg"]):
        amount = float(human["body_elements_kg"][symbol]) * fraction
        human["body_elements_kg"][symbol] = float(human["body_elements_kg"][symbol]) - amount
        detritus[symbol] = float(detritus.get(symbol, 0.0)) + amount
    human["energy"] = float(human["energy"]) + take * per_kg
    if abs(float(human["energy"])) < 1e-9:
        human["energy"] = 0.0
    return take


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



def _one_step_toward(origin: tuple[int, int], target: tuple[int, int]) -> tuple[int, int]:
    """One grid cell toward target (x first, then y). Both lie on the grid, so
    every intermediate cell does too."""
    (ox, oy), (tx, ty) = origin, target
    if ox != tx:
        return (ox + (1 if tx > ox else -1), oy)
    if oy != ty:
        return (ox, oy + (1 if ty > oy else -1))
    return origin


def _apply_physiology(
    human: dict,
    world_cell: dict,
    moved: bool,
    profile: dict | None = None,
    producer_cell: dict | None = None,
    insulation_c: float = 0.0,
    sleep_recovery: bool = False,
) -> None:
    """Apply bounded fatigue, thermoregulation cost, injury, and healing."""
    profile = profile or physiology_profile(calibrated=False, ticks_per_year=120)
    ambient = float(world_cell["temperature"])
    producer_cell = producer_cell or {}
    fire_intensity = max(0.0, min(1.0, float(producer_cell.get("fire_intensity", 0.0))))
    ambient += fire_intensity * 28.0
    canopy, terrain_cover = _structural_protection(world_cell, producer_cell)

    # Canopy primarily reduces hot exposure; cave/overhang terrain moderates
    # both hot and cold extremes toward a stable subsurface-like temperature.
    if ambient > HUMAN_COMFORT_TEMPERATURE_C:
        ambient -= min(9.0, canopy * 9.0)
    if terrain_cover > 0.0:
        moderation = min(0.55, terrain_cover * 0.55)
        ambient = ambient * (1.0 - moderation) + 15.0 * moderation
    uninsulated_ambient = ambient
    if insulation_c > 0.0 and ambient < HUMAN_COMFORT_TEMPERATURE_C:
        # Worn interlaced material slows heat loss in the cold (capacity v1).
        ambient = min(HUMAN_COMFORT_TEMPERATURE_C, ambient + insulation_c)

    thermal_delta = abs(ambient - HUMAN_COMFORT_TEMPERATURE_C)
    excess = max(0.0, thermal_delta - HUMAN_THERMAL_TOLERANCE_C)

    fatigue = float(human.get("fatigue", 0.0))
    if sleep_recovery:
        load = HUMAN_FATIGUE_MOVE_GAIN if moved else 0.0
        recovery = HUMAN_FATIGUE_SLEEP_RECOVERY_MOVED if moved else HUMAN_FATIGUE_SLEEP_RECOVERY_RESTED
        fatigue = min(1.0, fatigue + load) * (1.0 - recovery)
    elif moved:
        fatigue = min(1.0, fatigue + HUMAN_FATIGUE_MOVE_GAIN)
    else:
        fatigue = max(0.0, fatigue - HUMAN_FATIGUE_REST_RECOVERY)

    thermal_scale = max(0.08, float(profile.get("thermal_scale", 1.0)))
    thermal_cost_cap = (300.0 * thermal_scale) if bool(profile.get("calibrated")) else 0.30
    thermal_cost_rate = (10.0 * thermal_scale) if bool(profile.get("calibrated")) else 0.01
    if insulation_c > 0.0:
        # Experienced benefit of worn material: cold-stress energy not spent.
        bare_excess = max(0.0, abs(uninsulated_ambient - HUMAN_COMFORT_TEMPERATURE_C) - HUMAN_THERMAL_TOLERANCE_C)
        bare_cost = min(thermal_cost_cap, bare_excess * thermal_cost_rate)
        worn_cost = min(thermal_cost_cap, excess * thermal_cost_rate)
        human["insulation_saving_kcal"] = round(max(0.0, bare_cost - worn_cost), 10)
    if excess > 0.0:
        human["energy"] = float(human["energy"]) - min(thermal_cost_cap, excess * thermal_cost_rate)
        if ambient > HUMAN_COMFORT_TEMPERATURE_C:
            human["body_water_kg"] = max(
                0.0,
                float(human["body_water_kg"]) - min(
                    (0.75 * thermal_scale) if bool(profile.get("calibrated")) else 0.02,
                    excess * ((0.03 * thermal_scale) if bool(profile.get("calibrated")) else 0.001),
                ),
            )

    injury = float(human.get("injury", 0.0))
    severe_exposure = max(0.0, thermal_delta - 28.0)
    if severe_exposure > 0.0:
        injury_scale = max(0.15, float(profile.get("thermal_scale", 1.0)))
        injury = min(1.5, injury + min(0.08 * injury_scale, severe_exposure * 0.002 * injury_scale))
    if fire_intensity > 0.45:
        injury = min(1.5, injury + min(0.25, (fire_intensity - 0.45) * 0.30))

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



def _apply_predator_threat(human: dict, consumer_state: dict | None, epoch: int | None = None) -> int:
    if not consumer_state:
        return 0
    xy = (int(human["x"]), int(human["y"]))
    # Consumer timebase "elapsed-time-v2": a predator has one attack
    # opportunity per reference tick of elapsed time (traits.has_opportunity).
    ticks_per_year = int(consumer_state.get("ticks_per_year", 12))
    timebase = str(consumer_state.get("rate_timebase", "per-tick-legacy"))
    attack_chance = opportunity_probability(ticks_per_year, timebase)
    attackers = []
    for animal in consumer_state.get("animals", []):
        traits = trait_for(str(animal["species"]))
        if traits.trophic_role != "predator":
            continue
        if (int(animal["x"]), int(animal["y"])) != xy:
            continue
        if float(animal["energy"]) >= traits.reproduction_energy * 2.0:
            continue
        if attack_chance < 1.0 and opportunity_draw(animal["id"], human.get("id"), epoch, "attack") >= attack_chance:
            continue
        attackers.append(animal)

    if not attackers:
        return 0

    body_mass = _mass(human["body_elements_kg"]) + float(human["body_water_kg"])
    juvenile_scale = max(0.25, min(1.0, body_mass / 70.0))
    vulnerability = 1.0 / juvenile_scale
    injury_gain = min(0.45, len(attackers) * 0.08 * vulnerability)
    human["injury"] = min(1.5, float(human.get("injury", 0.0)) + injury_gain)
    return len(attackers)


def evolve_humans(
    human_state: dict,
    producer_state: dict,
    matter_state: dict,
    world_state: dict,
    epoch: int,
    *,
    cognition_enabled: bool = False,
    actions_enabled: bool = False,
    consumer_state: dict | None = None,
) -> tuple[dict, dict, dict]:
    humans, producers, matter, _ = evolve_agentus_step(
        human_state,
        producer_state,
        matter_state,
        world_state,
        epoch,
        cognition_enabled=cognition_enabled,
        actions_enabled=actions_enabled,
        consumer_state=consumer_state,
    )
    return humans, producers, matter


def evolve_agentus_step(
    human_state: dict,
    producer_state: dict,
    matter_state: dict,
    world_state: dict,
    epoch: int,
    *,
    cognition_enabled: bool = False,
    actions_enabled: bool = False,
    consumer_state: dict | None = None,
) -> tuple[dict, dict, dict, dict | None]:
    """One Agentus tick. Returns Consumer state too, because capacity model v1
    lets Agentus kill animals and eat carcass tissue inside the same atomic
    transaction. Without capacities the Consumer state is returned unchanged."""
    capacities = human_state.get("capacity_model") == cap.CAPACITY_MODEL
    ablation = set(str(human_state.get("capacity_ablation", "")).split("+"))
    if capacities and consumer_state is not None:
        consumer_state = deepcopy(consumer_state)
    humans = deepcopy(human_state)
    producers = deepcopy(producer_state)
    matter = deepcopy(matter_state)
    pcells = _cell_lookup(producers["cells"])
    mcells = _cell_lookup(matter["cells"])
    remains = _cell_lookup(humans["remains_cells"])
    wcells = _cell_lookup(world_state["cells"])
    profile = humans.get("physiology_profile", physiology_profile(calibrated=False, ticks_per_year=120))
    if capacities:
        ccells = _cell_lookup(consumer_state["carcass_cells"])
        lithic_cells = matter.setdefault("lithic_cells", {})

    survivors = []
    births = []
    fed_ids = set()
    people_by_id = {str(person["id"]): person for person in humans["humans"]}
    integrity = bool(humans.get("behavior_integrity"))
    # Where everyone stood at the start of the tick: a dependent is carried only
    # if it was with its caregiver before the caregiver moved.
    start_xy = {str(p["id"]): (int(p["x"]), int(p["y"])) for p in humans["humans"]}
    if integrity:
        # Caregivers act before their dependents, so a carried child ends the
        # day wherever its caregiver walked, and is nursed after she has eaten.
        order = sorted(humans["humans"], key=lambda h: (
            float(_age_profile(h, profile).get("caregiver_dependence", 0.0)) > 0.0, h["id"]))
    else:
        order = sorted(humans["humans"], key=lambda h: h["id"])
    for human in order:
        origin = (int(human["x"]), int(human["y"]))
        effective_profile = _age_profile(human, profile)
        store_stats = None
        if humans.get("energy_store_model") == ENERGY_STORE_SIZE_SCALED and "development_scale" in effective_profile:
            # One store for eating, hand-feeding and nursing
            # (docs/architecture/CHILD_ENERGY_STORE.md).
            effective_profile = dict(effective_profile)
            effective_profile["energy_store_capacity_kcal"] = energy_store_capacity(effective_profile)
            store_stats = humans.setdefault("energy_store_stats", {})
        start_energy = float(human["energy"])
        start_water = float(human["body_water_kg"])
        start_injury = float(human.get("injury", 0.0))
        caregiver = _resolve_caregiver(human, people_by_id, effective_profile)
        dependence = float(effective_profile.get("caregiver_dependence", 0.0))
        carried = bool(effective_profile.get("carried", dependence > 0.0))
        self_feeding = float(effective_profile.get("self_feeding", 1.0 - dependence))
        if carried and caregiver is not None:
            target = (int(caregiver["x"]), int(caregiver["y"]))
            if integrity and origin != start_xy.get(str(caregiver["id"]), target):
                # Not being carried: a separated dependent covers one cell a day.
                target = _one_step_toward(origin, target)
            perception = None
        elif cognition_enabled:
            perception = perceive_local(
                human,
                producers,
                matter,
                humans["humans"],
                world_state,
            )
            forage_need = (
                float(effective_profile["basal_energy_kcal_per_tick"])
                / max(
                    1e-9,
                    float(effective_profile["food_energy_kcal_per_kg"])
                    * float(effective_profile["assimilation"]),
                )
            )
            perception["forage_need_kg"] = forage_need
            perception["energy_reserve_fraction"] = (
                float(human["energy"])
                / max(1e-9, float(effective_profile.get("satiety_reference_kcal", effective_profile.get("energy_capacity_kcal", 1.0))))
            )
            if humans.get("thirst_planning"):
                _add_interoception(perception, human, effective_profile, profile)
            if integrity:
                perception["partial_food_anchor"] = True
            if humans.get("following"):
                # Who is in view, and where: visible facts only.
                perception["visible_peers"] = [
                    (str(p["id"]), int(p["x"]), int(p["y"])) for p in humans["humans"]
                    if p["id"] != human["id"]
                    and abs(int(p["x"]) - origin[0]) + abs(int(p["y"]) - origin[1]) <= 1
                ]
                perception["follow_draw"] = cap.mo.unit_draw(human["id"], epoch, "follow")
                perception["follow_pick"] = cap.mo.unit_draw(human["id"], epoch, "follow-pick")
            if capacities:
                scale = max(0.10, float(effective_profile.get("development_scale", 1.0)))
                extend_perception_with_materials(
                    perception,
                    producers,
                    consumer_state,
                    lithic_cells,
                    humans.get("objects", []),
                    human["cognition"].get("food_values", {}),
                    innate_food_prior(effective_profile)["plant_tissue"],
                    {
                        kind: float(spec["hand_access_kg"]) * scale
                        for kind, spec in FOOD_KINDS.items()
                        if spec["hand_access_kg"] is not None
                    },
                    None if "no_recall" in ablation else human["cognition"].get("memory", {}).get("locations", {}),
                )
            target = choose_destination(human, perception, human["cognition"])
        else:
            perception = None
            target = _move_toward_food(human, producers)
        moved = target != origin
        if moved:
            movement_cost = float(effective_profile["move_energy_kcal_per_tick"]) * (0.25 if carried else 1.0)
            human["energy"] = float(human["energy"]) - movement_cost
            human["x"], human["y"] = target

        xy = (int(human["x"]), int(human["y"]))
        if capacities:
            cap.carry_objects(humans, str(human["id"]), xy)
        if actions_enabled and human.get("learned_sequences"):
            sequence = human["learned_sequences"][-1]
            updated_human, updated_cell, trace = execute_live_sequence(
                sequence,
                human,
                pcells[xy],
            )
            human.update(updated_human)
            pcells[xy].update(updated_cell)
            human["energy"] = float(human["energy"]) - float(trace.get("effort_energy_kcal", 0.0))
            human["last_action_trace"] = trace
        nursing_model = humans.get("nursing_model")
        provisioned = _provision_dependent(
            human, caregiver, effective_profile, nursing_model,
            humans.setdefault("nursing_stats", {}) if nursing_model else None,
        )
        ate_kg_today = 0.0
        if self_feeding > 0.0 and capacities and "cognition" in human:
            _drink(human, mcells[xy], effective_profile)
            hungry = (
                float(human["energy"])
                / max(1e-9, float(effective_profile.get("satiety_reference_kcal", effective_profile.get("energy_capacity_kcal", 1.0))))
            ) < 0.75
            ctx = None
            samples: tuple[str, ...] = ()
            if dependence <= 0.0:
                if "no_interactions" not in ablation:
                    ctx = cap.run_interactions(
                        humans, human, effective_profile, pcells[xy], ccells[xy],
                        lithic_cells, wcells[xy], consumer_state, epoch, hungry,
                    )
                if "plant_diet" not in ablation:
                    samples = cap.choose_food_samples(human, pcells[xy], ccells[xy], epoch, hungry)
            intake = forage_at_cell(
                human, pcells[xy], ccells[xy], effective_profile,
                human["cognition"].get("food_values", {}),
                samples,
                {} if ctx is None else ctx.access_bonus,
            )
            if store_stats is not None:
                _record_refused(store_stats, effective_profile, sum(float(r.get("refused_kcal", 0.0)) for r in intake))
            if ctx is None:
                ctx = cap.Context(humans, human, effective_profile, pcells[xy], ccells[xy], lithic_cells, wcells[xy], consumer_state, epoch)
            cap.learn_from_tick(ctx, intake)
            ate = sum(float(r["kg"]) for r in intake if float(r["kcal"]) > 0.0)
            ate_kg_today = sum(float(r["kg"]) for r in intake)
            if perception is not None and "chosen_by" in perception:
                cap.learn_following(humans, human, perception, ate)
        elif self_feeding > 0.0:
            _drink(human, mcells[xy], effective_profile)
            ate = _eat(human, pcells[xy], effective_profile)
            ate_kg_today = ate
        else:
            ate = 0.0
        if humans.get("caregiving_model") == "solid-food-v1" and capacities:
            given = _provision_solid_food(
                human, caregiver, effective_profile,
                _age_profile(caregiver, profile) if caregiver is not None else effective_profile,
                pcells[xy], ccells[xy], ate_kg_today,
                humans.setdefault("capacity_stats", cap.empty_stats()),
                **({"store_stats": store_stats} if store_stats is not None else {}),
            )
            ate = float(ate) + given
        human["energy"] = float(human["energy"]) - float(effective_profile["basal_energy_kcal_per_tick"])
        if capacities:
            _apply_physiology(
                human, wcells[xy], moved, effective_profile, pcells[xy],
                insulation_c=cap.insulation_c(humans, str(human["id"])),
                sleep_recovery=integrity,
            )
            cap.credit_worn_benefit(humans, human, float(human.pop("insulation_saving_kcal", 0.0)), effective_profile)
        else:
            _apply_physiology(human, wcells[xy], moved, effective_profile, pcells[xy], sleep_recovery=integrity)
        attacks = _apply_predator_threat(human, consumer_state, epoch)
        if attacks:
            humans["predator_attack_events"] = int(humans.get("predator_attack_events", 0)) + attacks
        loss = min(float(human["body_water_kg"]), float(effective_profile["water_loss_per_tick_kg"]))
        human["body_water_kg"] -= loss
        matter["water_output_kg"] = float(matter["water_output_kg"]) + loss
        human["caregiver_present"] = bool(caregiver is not None and (int(caregiver["x"]), int(caregiver["y"])) == xy) if "caregiver_id" in human else False
        human["age_ticks"] = int(human["age_ticks"]) + 1

        if cognition_enabled and perception is not None:
            reward = _experienced_reward(
                start_energy=start_energy,
                start_water=start_water,
                start_injury=start_injury,
                human=human,
                profile=effective_profile,
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

        if "lean_catabolism_kcal_per_kg" in profile and float(human["energy"]) < 0.0:
            _catabolize_lean_tissue(human, profile, pcells[xy]["detritus_elements_kg"])
        body_mass = _mass(human["body_elements_kg"])
        energy_exhausted = (
            float(human["energy"]) < -1e-9 if "lean_catabolism_kcal_per_kg" in profile
            else float(human["energy"]) <= 0.0
        )
        dead = (
            energy_exhausted
            or float(human["body_water_kg"]) <= max(1e-6, float(effective_profile["water_capacity_kg"]) * float(profile["min_water_fraction"]))
            or body_mass <= float(effective_profile["min_dry_mass_kg"])
            or float(human.get("injury", 0.0)) >= HUMAN_INJURY_DEATH_THRESHOLD
            or int(human["age_ticks"]) >= int(profile["max_age_ticks"])
        )
        if dead:
            if energy_exhausted:
                death_cause = "energy"
            elif float(human["body_water_kg"]) <= max(1e-6, float(effective_profile["water_capacity_kg"]) * float(profile["min_water_fraction"])):
                death_cause = "dehydration"
            elif body_mass <= float(effective_profile["min_dry_mass_kg"]):
                death_cause = "low_body_mass"
            elif float(human.get("injury", 0.0)) >= HUMAN_INJURY_DEATH_THRESHOLD:
                death_cause = "injury"
            else:
                death_cause = "old_age"
            death_counts = dict(humans.get("cumulative_deaths_by_cause", {}))
            death_counts[death_cause] = int(death_counts.get(death_cause, 0)) + 1
            humans["cumulative_deaths_by_cause"] = death_counts
            records = list(humans.get("death_records", []))
            records.append({
                "id": str(human["id"]),
                "generation": int(human.get("generation", 0)),
                "cause": death_cause,
                "caregiver_id": human.get("caregiver_id"),
                "epoch": int(epoch),
            })
            humans["death_records"] = records[-256:]
            cell = remains[xy]
            for symbol in HUMAN_TRACKED_ELEMENTS:
                cell["elements_kg"][symbol] += float(human["body_elements_kg"][symbol])
                cell["elements_kg"][symbol] += float(
                    human.get("held_material_elements_kg", {}).get(symbol, 0.0)
                )
            cell["water_kg"] += float(human["body_water_kg"])
            humans["cumulative_deaths"] = int(humans.get("cumulative_deaths", 0)) + 1
            if capacities:
                cap.drop_all(humans, str(human["id"]))
            continue

        survivors.append(human)
        if ate > 0.0:
            fed_ids.add(str(human["id"]))

    # Reproduction sees the living adults' positions after today's movement.
    adults_by_cell: dict[tuple[int, int], set[str]] = {}
    for person in survivors:
        if int(person["age_ticks"]) >= int(profile["maturity_ticks"]):
            adults_by_cell.setdefault((int(person["x"]), int(person["y"])), set()).add(str(person["sex"]))
    for human in survivors:
        xy = (int(human["x"]), int(human["y"]))
        body_mass = _mass(human["body_elements_kg"])
        since_birth = epoch - int(human.get("last_reproduction_epoch", -1000000))
        can_reproduce = (
            human["sex"] == "female"
            and int(human["age_ticks"]) >= int(profile["maturity_ticks"])
            and {"female", "male"}.issubset(adults_by_cell.get(xy, set()))
            and float(human["energy"]) >= float(profile["reproduction_energy_kcal"])
            and body_mass >= float(profile["seed_dry_mass_kg"]) * 0.9
            and str(human["id"]) in fed_ids
            and since_birth >= int(profile["reproduction_cooldown_ticks"])
        )
        if can_reproduce:
            ordinal = int(humans["next_birth_ordinal"])
            humans["next_birth_ordinal"] = ordinal + 1
            child = _offspring(human, ordinal, profile)
            if capacities and "cognition" in child:
                cap.init_capacity_cognition(child, profile)
            human["energy"] = max(0.0, float(human["energy"]) - float(child["energy"]))
            human["last_reproduction_epoch"] = epoch
            births.append(child)
            humans["cumulative_births"] = int(humans.get("cumulative_births", 0)) + 1

    humans["humans"] = survivors + births
    if capacities:
        cap.weather_objects(humans, pcells, wcells, epoch)

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
        human["held_material_elements_kg"] = {
            s: round(max(0.0, float(v)), 10)
            for s, v in sorted(human.get("held_material_elements_kg", {}).items())
        }
    for cell in humans["remains_cells"]:
        cell["water_kg"] = round(max(0.0, float(cell["water_kg"])), 10)
        cell["elements_kg"] = {
            s: round(max(0.0, float(v)), 10)
            for s, v in sorted(cell["elements_kg"].items())
        }
    matter["water_output_kg"] = round(float(matter["water_output_kg"]), 10)
    return humans, producers, matter, consumer_state


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
    for symbol, amount in cap.object_element_totals(state).items():
        totals[symbol] = totals.get(symbol, 0.0) + float(amount)
    return {s: round(v, 10) for s, v in sorted(totals.items())}


def human_water_total_kg(state: dict) -> float:
    return (
        sum(float(h["body_water_kg"]) for h in state["humans"])
        + sum(float(c["water_kg"]) for c in state["remains_cells"])
    )
