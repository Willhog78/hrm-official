from __future__ import annotations


def ecology_metrics(producer_state: dict, consumer_state: dict) -> dict:
    plant_cells = 0
    plant_mass = 0.0
    for cell in producer_state["cells"]:
        mass = sum(float(v) for v in cell["plant_elements_kg"].values())
        plant_mass += mass
        if mass > 0.0:
            plant_cells += 1

    by_species: dict[str, int] = {}
    occupied = set()
    for animal in consumer_state["consumers"]:
        species = str(animal["species"])
        by_species[species] = by_species.get(species, 0) + 1
        occupied.add((int(animal["x"]), int(animal["y"])))

    return {
        "plant_biomass_kg": round(plant_mass, 10),
        "plant_occupied_cells": plant_cells,
        "consumer_counts": dict(sorted(by_species.items())),
        "consumer_occupied_cells": len(occupied),
    }
