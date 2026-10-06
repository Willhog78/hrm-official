from __future__ import annotations

import json

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.ecology.autonomy import ecology_snapshot, occupied_consumer_cells, occupied_producer_cells
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
    return {
        s: m.get(s, 0.0) + p.get(s, 0.0) + a.get(s, 0.0) - initial.get(s, 0.0)
        for s in symbols
    }


def combined_water_error(sim: GenesisSimulation) -> float:
    matter = sim.matter_state()
    stored = total_water(matter["cells"]) + consumer_water_total_kg(sim.consumer_state())
    expected = (
        float(matter["initial_water_kg"])
        + float(matter["water_input_kg"])
        - float(matter["water_output_kg"])
    )
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

    start = ecology_snapshot(sim.ecology_state(), sim.consumer_state())
    start_consumers = population_counts(sim.consumer_state())
    start_producer_cells = len(occupied_producer_cells(sim.ecology_state()))
    start_consumer_cells = len(occupied_consumer_cells(sim.consumer_state()))

    yearly = []
    for year in range(1, 101):
        sim.run(config.ticks_per_year)
        snap = ecology_snapshot(sim.ecology_state(), sim.consumer_state())
        snap["year"] = year
        snap["producer_occupied_cells"] = len(occupied_producer_cells(sim.ecology_state()))
        snap["consumer_occupied_cells"] = len(occupied_consumer_cells(sim.consumer_state()))
        yearly.append(snap)

    final = ecology_snapshot(sim.ecology_state(), sim.consumer_state())
    final_consumers = population_counts(sim.consumer_state())
    errors = combined_element_errors(sim)
    matter = sim.matter_state()

    report = {
        "years": 100,
        "ticks": sim.snapshot().epoch,
        "start": {
            **start,
            "consumer_populations": start_consumers,
            "producer_occupied_cells": start_producer_cells,
            "consumer_occupied_cells": start_consumer_cells,
        },
        "final": {
            **final,
            "consumer_populations": final_consumers,
            "producer_occupied_cells": len(occupied_producer_cells(sim.ecology_state())),
            "consumer_occupied_cells": len(occupied_consumer_cells(sim.consumer_state())),
        },
        "ranges": {
            "producer_biomass_kg": {
                "min": min(float(x["producer_biomass_kg"]) for x in yearly),
                "max": max(float(x["producer_biomass_kg"]) for x in yearly),
            },
            "consumer_population_total": {
                "min": min(sum(int(v) for v in x["consumer_populations"].values()) for x in yearly),
                "max": max(sum(int(v) for v in x["consumer_populations"].values()) for x in yearly),
            },
            "producer_occupied_cells": {
                "min": min(int(x["producer_occupied_cells"]) for x in yearly),
                "max": max(int(x["producer_occupied_cells"]) for x in yearly),
            },
            "consumer_occupied_cells": {
                "min": min(int(x["consumer_occupied_cells"]) for x in yearly),
                "max": max(int(x["consumer_occupied_cells"]) for x in yearly),
            },
        },
        "water": {
            "environment_kg": total_water(matter["cells"]),
            "consumer_body_and_carcass_kg": consumer_water_total_kg(sim.consumer_state()),
            "input_kg": float(matter["water_input_kg"]),
            "output_kg": float(matter["water_output_kg"]),
            "balance_error_kg": combined_water_error(sim),
        },
        "conservation": {
            "max_abs_element_error_kg": max(abs(v) for v in errors.values()),
            "element_errors_kg": errors,
        },
        "ledger_valid": sim.ledger.verify_chain(),
    }

    print("G4_RESULTS_JSON=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
