from __future__ import annotations

import json

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.ecology.plants import ecology_element_totals, producer_biomass_kg
from hrm_genesis.human import human_element_totals, human_water_total_kg
from hrm_genesis.matter.pools import total_elements, total_water
from hrm_genesis.observer import observe_genesis


YEARS = 5
TICKS_PER_YEAR = 365


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
        "humans": len(people),
        "births_cumulative": int(humans.get("cumulative_births", 0)),
        "deaths_cumulative": int(humans.get("cumulative_deaths", 0)),
        "by_generation": dict(sorted(by_generation.items())),
        "mean_mass_kg": round(sum(masses) / len(masses), 6) if masses else None,
        "min_mass_kg": round(min(masses), 6) if masses else None,
        "max_mass_kg": round(max(masses), 6) if masses else None,
        "mean_energy_kcal": round(sum(energies) / len(energies), 6) if energies else None,
        "mean_body_water_kg": round(sum(waters) / len(waters), 6) if waters else None,
        "max_injury": round(max(injuries), 6) if injuries else None,
        "producer_biomass_kg": round(producer_biomass_kg(ecology), 6),
        "consumer_counts": observed["ecology"]["consumer_counts"],
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
        world_width=32,
        world_height=32,
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

    for year in range(1, YEARS + 1):
        sim.run(TICKS_PER_YEAR)
        report = summarize(sim, year)
        reports.append(report)
        print("LONG_RUN_YEAR:", json.dumps(report, sort_keys=True), flush=True)
        if report["humans"] == 0:
            print("LONG_RUN_EXTINCTION_YEAR:", year, flush=True)
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
        "completed_years": int(final["year"]),
        "human_outcome": "surviving" if int(final["humans"]) > 0 else "extinct",
        "final_humans": int(final["humans"]),
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
