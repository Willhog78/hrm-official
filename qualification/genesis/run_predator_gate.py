from __future__ import annotations

from copy import deepcopy

from hrm_coordination.seeds import SeedBank
from hrm_genesis.ecology.animals import (
    build_consumer_state,
    evolve_consumers,
    seed_initial_consumers,
    consumer_element_totals,
)
from hrm_genesis.ecology.plants import build_producer_state, ecology_element_totals
from hrm_genesis.human.biology import _apply_predator_threat


def main() -> int:
    seed = SeedBank("predator-gate")
    producers = build_producer_state(width=3, height=3)
    for cell in producers["cells"]:
        for symbol in cell["plant_elements_kg"]:
            cell["plant_elements_kg"][symbol] = 3.0

    matter = {
        "width": 3,
        "height": 3,
        "epoch_applied": -1,
        "water_input_kg": 0.0,
        "water_output_kg": 0.0,
        "initial_water_kg": 0.0,
        "initial_elements_kg": {},
        "cells": [
            {
                "x": x, "y": y,
                "surface_water_kg": 10.0,
                "soil_water_kg": 50.0,
                "elements_kg": {"C":100.0,"N":100.0,"P":100.0,"K":100.0,"Ca":100.0,"Mg":100.0,"S":100.0,"Fe":100.0,"Si":100.0},
            }
            for y in range(3) for x in range(3)
        ],
    }
    consumers = build_consumer_state(width=3, height=3, seed_bank=seed, initial_per_species=2)
    consumers, producers, matter = seed_initial_consumers(consumers, producers, matter)

    stalkers = [a for a in consumers["animals"] if a["species"] == "stalker"]
    browsers = [a for a in consumers["animals"] if a["species"] == "browser"]
    assert stalkers and browsers

    stalker = stalkers[0]
    browser = browsers[0]
    stalker["x"] = browser["x"] = 1
    stalker["y"] = browser["y"] = 1
    stalker["energy"] = 1.0
    browser["energy"] = 8.0

    before_consumers = consumer_element_totals(consumers)
    before_ecology = ecology_element_totals(producers)
    symbols = sorted(set(before_consumers) | set(before_ecology))
    matter_before = {
        symbol: sum(float(c["elements_kg"].get(symbol, 0.0)) for c in matter["cells"])
        for symbol in symbols
    }
    before_total = {
        symbol: float(before_consumers.get(symbol, 0.0))
        + float(before_ecology.get(symbol, 0.0))
        + float(matter_before.get(symbol, 0.0))
        for symbol in symbols
    }
    world = {
        "cells": [
            {"x": x, "y": y, "temperature": 22.0}
            for y in range(3) for x in range(3)
        ]
    }
    after, _, matter_after = evolve_consumers(
        consumers, producers, matter, world, epoch=1
    )
    after_consumers = consumer_element_totals(after)
    after_ecology = ecology_element_totals(producers_after)
    matter_after_totals = {
        symbol: sum(float(c["elements_kg"].get(symbol, 0.0)) for c in matter_after["cells"])
        for symbol in symbols
    }
    after_total = {
        symbol: float(after_consumers.get(symbol, 0.0))
        + float(after_ecology.get(symbol, 0.0))
        + float(matter_after_totals.get(symbol, 0.0))
        for symbol in symbols
    }

    predation_deaths = int(after.get("last_tick_deaths_by_cause", {}).get("predation", 0))
    browser_ids_after = {a["id"] for a in after["animals"] if a["species"] == "browser"}

    agentus = {
        "x": 1, "y": 1,
        "body_elements_kg": {"C":24.08,"N":2.24,"K":0.7,"P":0.336,"Mg":0.364,"S":0.28},
        "body_water_kg": 42.0,
        "injury": 0.0,
    }
    hungry_predators = deepcopy(after)
    for animal in hungry_predators["animals"]:
        if animal["species"] == "stalker":
            animal["x"], animal["y"], animal["energy"] = 1, 1, 1.0
    attacks = _apply_predator_threat(agentus, hungry_predators)

    checks = {
        "predator_exists": len(stalkers) >= 1,
        "browser_can_be_killed": browser["id"] not in browser_ids_after and predation_deaths >= 1,
        "predation_preserves_full_element_system": all(
            abs(float(after_total[symbol]) - float(before_total[symbol])) < 1e-6
            for symbol in symbols
        ),
        "agentus_can_be_attacked": attacks >= 1 and float(agentus["injury"]) > 0.0,
        "no_target_population_field": "target_population" not in after,
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print("PREDATOR_RESULTS:", {
        "predation_deaths": predation_deaths,
        "browsers_after": sum(1 for a in after["animals"] if a["species"] == "browser"),
        "stalkers_after": sum(1 for a in after["animals"] if a["species"] == "stalker"),
        "agentus_injury": round(float(agentus["injury"]), 6),
    })

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("PREDATOR_GATE_FAIL:", ", ".join(failed))
        return 1
    print("PREDATOR_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
