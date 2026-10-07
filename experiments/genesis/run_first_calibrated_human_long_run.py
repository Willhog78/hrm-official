from __future__ import annotations

import json

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.ecology.plants import (
    ecology_element_totals,
    producer_biomass_kg,
    producer_edible_biomass_kg,
    producer_woody_biomass_kg,
)
from hrm_genesis.human import human_element_totals, human_water_total_kg
from hrm_genesis.matter.pools import total_elements, total_water
from hrm_genesis.observer import observe_genesis


YEARS = 5
TICKS_PER_YEAR = 365
REPORT_INTERVAL_DAYS = 30


def combined_element_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    pools = [
        total_elements(matter["cells"]),
        ecology_element_totals(sim.ecology_state()),
        consumer_element_totals(sim.consumer_state()),
        human_element_totals(sim.human_state()),
    ]
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial).union(*(set(p) for p in pools)))
    return {
        symbol: sum(pool.get(symbol, 0.0) for pool in pools) - initial.get(symbol, 0.0)
        for symbol in symbols
    }


def combined_water_error(sim: GenesisSimulation) -> float:
    matter = sim.matter_state()
    stored = (
        total_water(matter["cells"])
        + consumer_water_total_kg(sim.consumer_state())
        + human_water_total_kg(sim.human_state())
    )
    expected = (
        float(matter["initial_water_kg"])
        + float(matter["water_input_kg"])
        - float(matter["water_output_kg"])
    )
    return stored - expected


def total_mass(human: dict) -> float:
    return (
        sum(float(v) for v in human["body_elements_kg"].values())
        + float(human["body_water_kg"])
        + sum(float(v) for v in human.get("held_material_elements_kg", {}).values())
    )



def agentus_resource_diagnostics(sim: GenesisSimulation) -> dict:
    ecology = sim.ecology_state()
    people = list(sim.human_state()["humans"])
    pcells = {
        (int(cell["x"]), int(cell["y"])): cell
        for cell in ecology["cells"]
    }

    edible = {
        xy: sum(float(v) for v in cell["plant_elements_kg"].values())
        for xy, cell in pcells.items()
    }
    viable = [xy for xy, mass in edible.items() if mass >= 0.10]

    rows = []
    for person in people:
        xy = (int(person["x"]), int(person["y"]))
        neighborhood = [
            (xy[0], xy[1]),
            (xy[0] - 1, xy[1]),
            (xy[0] + 1, xy[1]),
            (xy[0], xy[1] - 1),
            (xy[0], xy[1] + 1),
        ]
        neighborhood = [p for p in neighborhood if p in pcells]
        nearest = (
            min(abs(v[0] - xy[0]) + abs(v[1] - xy[1]) for v in viable)
            if viable else None
        )
        rows.append({
            "id": str(person["id"]),
            "xy": [xy[0], xy[1]],
            "energy": round(float(person["energy"]), 3),
            "local_edible_kg": round(float(edible.get(xy, 0.0)), 6),
            "visible_max_edible_kg": round(max(float(edible[p]) for p in neighborhood), 6),
            "nearest_viable_food_steps": nearest,
        })
    return {
        "edible_biomass_kg": round(producer_edible_biomass_kg(ecology), 6),
        "woody_biomass_kg": round(producer_woody_biomass_kg(ecology), 6),
        "viable_food_cells": len(viable),
        "agentus_resources": rows,
    }


def summarize(sim: GenesisSimulation, year: int) -> dict:
    humans = sim.human_state()
    ecology = sim.ecology_state()
    consumers = sim.consumer_state()
    observed = observe_genesis(
        world_state=sim.world_state(),
        matter_state=sim.matter_state(),
        producer_state=ecology,
        consumer_state=consumers,
        human_state=humans,
    )

    people = list(humans["humans"])
    by_generation: dict[str, int] = {}
    masses = []
    energies = []
    waters = []
    injuries = []
    for human in people:
        generation = str(int(human.get("generation", 0)))
        by_generation[generation] = by_generation.get(generation, 0) + 1
        masses.append(total_mass(human))
        energies.append(float(human["energy"]))
        waters.append(float(human["body_water_kg"]))
        injuries.append(float(human.get("injury", 0.0)))

    element_errors = combined_element_errors(sim)

    return {
        "year": year,
        "epoch": sim.orchestrator.epoch,
        "agentus": len(people),
        "births_cumulative": int(humans.get("cumulative_births", 0)),
        "deaths_cumulative": int(humans.get("cumulative_deaths", 0)),
        "agentus_deaths_by_cause": dict(humans.get("cumulative_deaths_by_cause", {})),
        "agentus_death_records": list(humans.get("death_records", [])),
        "dependent_agentus": sum(
            1 for person in people
            if int(person.get("age_ticks", 0)) < int(humans["physiology_profile"].get("dependent_age_ticks", 0))
        ),
        "by_generation": dict(sorted(by_generation.items())),
        "mean_mass_kg": round(sum(masses) / len(masses), 6) if masses else None,
        "min_mass_kg": round(min(masses), 6) if masses else None,
        "max_mass_kg": round(max(masses), 6) if masses else None,
        "mean_energy_kcal": round(sum(energies) / len(energies), 6) if energies else None,
        "mean_body_water_kg": round(sum(waters) / len(waters), 6) if waters else None,
        "max_injury": round(max(injuries), 6) if injuries else None,
        "producer_biomass_kg": round(producer_biomass_kg(ecology), 6),
        "resource_diagnostics": agentus_resource_diagnostics(sim),
        "consumer_counts": observed["ecology"]["consumer_counts"],
        "consumer_deaths_by_cause": dict(consumers.get("cumulative_deaths_by_cause", {})),
        "agentus_predator_attack_events": int(humans.get("predator_attack_events", 0)),
        "active_fire_cells": observed["ecology"].get("active_fire_cells", 0),
        "max_fire_intensity": observed["ecology"].get("max_fire_intensity", 0.0),
        "arranged_material_kg": observed["ecology"].get("arranged_material_kg", 0.0),
        "protective_arrangement_cells": observed["ecology"].get("protective_arrangement_cells", 0),
        "agents_with_teacher": observed["population"]["agents_with_teacher"],
        "learned_sequence_count": observed["population"]["learned_sequence_count"],
        "max_abs_element_error_kg": max(abs(v) for v in element_errors.values()),
        "water_error_kg": combined_water_error(sim),
        "ledger_valid": sim.ledger.verify_chain(),
    }


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-first-calibrated-human-long-run",
        world_width=16,
        world_height=16,
        ticks_per_year=TICKS_PER_YEAR,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_cognition_enabled=True,
        human_actions_enabled=True,
        multi_population_enabled=True,
        material_scale_factor=1000.0,
        human_calibration_enabled=True,
    )

    sim = GenesisSimulation(config)
    reports = [summarize(sim, 0)]
    print("LONG_RUN_YEAR:", json.dumps(reports[-1], sort_keys=True), flush=True)

    day = 0
    while day < YEARS * TICKS_PER_YEAR:
        step = min(REPORT_INTERVAL_DAYS, YEARS * TICKS_PER_YEAR - day)
        sim.run(step)
        day += step
        report = summarize(sim, round(day / TICKS_PER_YEAR, 6))
        report["day"] = day
        reports.append(report)
        print("LONG_RUN_CHECKPOINT:", json.dumps(report, sort_keys=True), flush=True)
        if report["agentus"] == 0:
            print("LONG_RUN_EXTINCTION_DAY:", day, flush=True)
            break

    integrity = {
        "ledger_valid": all(bool(r["ledger_valid"]) for r in reports),
        "element_accounting": all(abs(float(r["max_abs_element_error_kg"])) < 5e-3 for r in reports),
        "water_accounting": all(abs(float(r["water_error_kg"])) < 5e-3 for r in reports),
    }
    for name, passed in integrity.items():
        print(f"LONG_RUN_INTEGRITY_{name.upper()}: {'PASS' if passed else 'FAIL'}", flush=True)

    final = reports[-1]
    outcome = {
        "planned_years": YEARS,
        "completed_years": float(final["year"]),
        "agentus_outcome": "surviving" if int(final["agentus"]) > 0 else "extinct",
        "final_agentus": int(final["agentus"]),
        "births": int(final["births_cumulative"]),
        "deaths": int(final["deaths_cumulative"]),
        "generations_present": final["by_generation"],
    }
    print("LONG_RUN_OUTCOME:", json.dumps(outcome, sort_keys=True), flush=True)

    if not all(integrity.values()):
        print("LONG_RUN_INVALID_INTEGRITY_FAILURE", flush=True)
        return 1

    print("LONG_RUN_COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
