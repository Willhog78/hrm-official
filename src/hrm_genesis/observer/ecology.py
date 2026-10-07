from __future__ import annotations


def ecology_metrics(producer_state: dict, consumer_state: dict) -> dict:
    plant_cells = 0
    plant_mass = 0.0
    for cell in producer_state["cells"]:
        mass = sum(float(v) for v in cell["plant_elements_kg"].values())
        plant_mass += mass
        if mass > 0.0:
            plant_cells += 1

    arranged_cells = 0
    arranged_mass = 0.0
    active_fire_cells = 0
    max_fire_intensity = 0.0
    for cell in producer_state["cells"]:
        local_arranged = sum(float(v) for v in cell.get("arranged_material_elements_kg", {}).values())
        arranged_mass += local_arranged
        if local_arranged > 0.0:
            arranged_cells += 1
        fire = max(0.0, float(cell.get("fire_intensity", 0.0)))
        if fire > 0.0:
            active_fire_cells += 1
        max_fire_intensity = max(max_fire_intensity, fire)

    by_species: dict[str, int] = {}
    occupied = set()
    for animal in consumer_state["animals"]:
        species = str(animal["species"])
        by_species[species] = by_species.get(species, 0) + 1
        occupied.add((int(animal["x"]), int(animal["y"])))

    return {
        "plant_biomass_kg": round(plant_mass, 10),
        "plant_occupied_cells": plant_cells,
        "consumer_counts": dict(sorted(by_species.items())),
        "consumer_occupied_cells": len(occupied),
        "arranged_material_kg": round(arranged_mass, 10),
        "arranged_material_cells": arranged_cells,
        "active_fire_cells": active_fire_cells,
        "max_fire_intensity": round(max_fire_intensity, 10),
    }
