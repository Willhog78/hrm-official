from __future__ import annotations

from copy import deepcopy

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.biology import evolve_humans, human_element_totals, human_water_total_kg
from hrm_genesis.ecology.plants import ecology_element_totals
from hrm_genesis.matter.pools import total_elements, total_water


def system_elements(humans: dict, producers: dict, matter: dict) -> dict[str, float]:
    pools = [
        human_element_totals(humans),
        ecology_element_totals(producers),
        total_elements(matter["cells"]),
    ]
    symbols = sorted(set().union(*(set(p) for p in pools)))
    return {s: sum(float(p.get(s, 0.0)) for p in pools) for s in symbols}


def system_water(humans: dict, matter: dict) -> float:
    return total_water(matter["cells"]) + human_water_total_kg(humans)


def main() -> int:
    config = GenesisConfig(
        master_seed="agentus-dependent-development-gate",
        world_width=16,
        world_height=16,
        ticks_per_year=365,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_calibration_enabled=True,
    )
    sim = GenesisSimulation(config)
    humans = deepcopy(sim.human_state())
    producers = deepcopy(sim.ecology_state())
    matter = deepcopy(sim.matter_state())
    world = deepcopy(sim.world_state())

    richest = max(
        producers["cells"],
        key=lambda c: sum(float(v) for v in c["plant_elements_kg"].values()),
    )
    xy = (int(richest["x"]), int(richest["y"]))
    profile = humans["physiology_profile"]
    for person in humans["humans"]:
        person["x"], person["y"] = xy
        person["age_ticks"] = int(profile["maturity_ticks"]) + 1
        person["energy"] = 28000.0
        person["last_reproduction_epoch"] = -1000000

    before_elements = system_elements(humans, producers, matter)
    before_water = system_water(humans, matter)

    humans, producers, matter = evolve_humans(
        humans, producers, matter, world, epoch=1
    )
    children = [h for h in humans["humans"] if int(h.get("generation", 0)) == 1]
    if not children:
        print("AGENTUS_DEVELOPMENT_FAIL: no_birth")
        return 1

    child_id = str(children[0]["id"])
    caregiver_id = str(children[0].get("caregiver_id", ""))
    birth_mass = (
        sum(float(v) for v in children[0]["body_elements_kg"].values())
        + float(children[0]["body_water_kg"])
    )

    max_days = 180
    for day in range(2, max_days + 2):
        humans, producers, matter = evolve_humans(
            humans, producers, matter, world, epoch=day
        )
        if not any(str(h["id"]) == child_id for h in humans["humans"]):
            break

    survivors = {str(h["id"]): h for h in humans["humans"]}
    child = survivors.get(child_id)
    caregiver = survivors.get(caregiver_id)
    final_elements = system_elements(humans, producers, matter)
    final_water = system_water(humans, matter)

    if child is not None:
        final_mass = (
            sum(float(v) for v in child["body_elements_kg"].values())
            + float(child["body_water_kg"])
        )
    else:
        final_mass = 0.0

    checks = {
        "generation_one_born": bool(child_id),
        "caregiver_link_recorded": bool(caregiver_id),
        "dependent_survives_180_days": child is not None,
        "caregiver_survives": caregiver is not None,
        "dependent_grows": child is not None and final_mass > birth_mass,
        "caregiver_presence_recorded": child is not None and bool(child.get("caregiver_present")),
        "elements_conserved": all(
            abs(float(final_elements.get(s, 0.0)) - float(before_elements.get(s, 0.0))) < 5e-4
            for s in set(before_elements) | set(final_elements)
        ),
        "water_accounted": abs(
            (final_water + float(matter["water_output_kg"]))
            - (before_water + float(sim.matter_state()["water_output_kg"]))
        ) < 5e-4,
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print("AGENTUS_DEVELOPMENT_RESULTS:", {
        "child_id": child_id,
        "caregiver_id": caregiver_id,
        "birth_mass_kg": round(birth_mass, 6),
        "final_mass_kg": round(final_mass, 6),
        "child_age_days": int(child["age_ticks"]) if child else None,
    })

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("AGENTUS_DEVELOPMENT_FAIL:", ", ".join(failed))
        return 1
    print("AGENTUS_DEVELOPMENT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
