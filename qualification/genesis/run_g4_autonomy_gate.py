from __future__ import annotations

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.autonomy import ecology_snapshot, occupied_consumer_cells
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.ecology.plants import ecology_element_totals
from hrm_genesis.ecology.populations import population_counts
from hrm_genesis.matter.pools import total_elements, total_water


def combined_element_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    m = total_elements(matter["cells"])
    p = ecology_element_totals(sim.ecology_state())
    a = consumer_element_totals(sim.consumer_state())
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial) | set(m) | set(p) | set(a))
    return {s: m.get(s,0.0)+p.get(s,0.0)+a.get(s,0.0)-initial.get(s,0.0) for s in symbols}


def combined_water_error(sim: GenesisSimulation) -> float:
    matter = sim.matter_state()
    stored = total_water(matter["cells"]) + consumer_water_total_kg(sim.consumer_state())
    expected = float(matter["initial_water_kg"]) + float(matter["water_input_kg"]) - float(matter["water_output_kg"])
    return stored - expected


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g4-century",
        world_width=4,
        world_height=4,
        ticks_per_year=12,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
    )
    sim = GenesisSimulation(config)
    samples = []
    occupied = []
    yearly_populations = []

    for year in range(1, 101):
        sim.run(config.ticks_per_year)
        snap = ecology_snapshot(sim.ecology_state(), sim.consumer_state())
        samples.append(snap)
        occupied.append(occupied_consumer_cells(sim.consumer_state()))
        yearly_populations.append({
            "year": year,
            "populations": population_counts(sim.consumer_state()),
            "producer_biomass_kg": float(snap["producer_biomass_kg"]),
            "consumer_occupied_cells": len(occupied[-1]),
        })

    biomass_values = [float(s["producer_biomass_kg"]) for s in samples]
    population_values = [
        sum(int(v) for v in s["consumer_populations"].values())
        for s in samples
    ]

    final_populations = population_counts(sim.consumer_state())

    checks = {
        "century_completed": sim.snapshot().epoch == 100 * config.ticks_per_year,
        "ledger_valid": sim.ledger.verify_chain(),
        "element_conservation": all(abs(v) < 5e-5 for v in combined_element_errors(sim).values()),
        "water_accounting": abs(combined_water_error(sim)) < 5e-5,
        "producer_state_changed": max(biomass_values) != min(biomass_values),
        "consumer_state_changed": max(population_values) != min(population_values) or len({frozenset(x) for x in occupied}) > 1,
        "grazer_survives_century": final_populations.get("grazer", 0) > 0,
        "browser_survives_century": final_populations.get("browser", 0) > 0,
        "no_human_state": not any(aid.startswith("human.") for aid in sim.fabric.authority_ids),
    }

    failed = [k for k,v in checks.items() if not v]
    for k,v in checks.items():
        print(f"{k}: {'PASS' if v else 'FAIL'}")

    if not checks["grazer_survives_century"]:
        extinction_year = next(
            (row["year"] for row in yearly_populations if row["populations"].get("grazer", 0) == 0),
            None,
        )
        print(f"grazer_extinction_year: {extinction_year}")
        if extinction_year is not None:
            for row in yearly_populations[max(0, extinction_year - 6):extinction_year]:
                print(
                    "grazer_trace: "
                    f"year={row['year']} "
                    f"grazer={row['populations'].get('grazer', 0)} "
                    f"browser={row['populations'].get('browser', 0)} "
                    f"producer_biomass_kg={row['producer_biomass_kg']:.6f} "
                    f"consumer_cells={row['consumer_occupied_cells']}"
                )
    if failed:
        print("G4_GATE_FAIL:", ", ".join(failed))
        return 1
    print("G4_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
