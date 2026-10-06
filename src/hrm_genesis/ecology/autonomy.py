from __future__ import annotations

from .animals import consumer_element_totals, consumer_water_total_kg
from .plants import (
    ecology_element_totals,
    producer_biomass_kg,
    producer_detritus_mass_kg,
    producer_seed_mass_kg,
)
from .populations import population_counts


def ecology_snapshot(
    producer_state: dict,
    consumer_state: dict,
) -> dict[str, object]:
    return {
        "producer_biomass_kg": producer_biomass_kg(producer_state),
        "producer_seed_mass_kg": producer_seed_mass_kg(producer_state),
        "producer_detritus_mass_kg": producer_detritus_mass_kg(producer_state),
        "consumer_populations": population_counts(consumer_state),
        "producer_elements_kg": ecology_element_totals(producer_state),
        "consumer_elements_kg": consumer_element_totals(consumer_state),
        "consumer_water_kg": consumer_water_total_kg(consumer_state),
    }


def occupied_consumer_cells(consumer_state: dict) -> set[tuple[int, int]]:
    return {
        (int(animal["x"]), int(animal["y"]))
        for animal in consumer_state["animals"]
    }


def occupied_producer_cells(producer_state: dict, threshold_kg: float = 1e-6) -> set[tuple[int, int]]:
    occupied: set[tuple[int, int]] = set()
    for cell in producer_state["cells"]:
        biomass = sum(float(v) for v in cell["plant_elements_kg"].values())
        if biomass > threshold_kg:
            occupied.add((int(cell["x"]), int(cell["y"])))
    return occupied


def dynamic_span(samples: list[dict[str, object]], field: str) -> float:
    values = [float(sample[field]) for sample in samples]
    return 0.0 if not values else max(values) - min(values)
