from __future__ import annotations

from copy import deepcopy

from .ecology import ecology_metrics
from .population import population_metrics
from .emergence import classify_emergence


def observe_genesis(*, world_state: dict, matter_state: dict, producer_state: dict, consumer_state: dict, human_state: dict) -> dict:
    """Return a read-only descriptive report from copied state."""
    world = deepcopy(world_state)
    matter = deepcopy(matter_state)
    producers = deepcopy(producer_state)
    consumers = deepcopy(consumer_state)
    humans = deepcopy(human_state)

    temperatures = [float(c["temperature"]) for c in world["cells"]]
    surface_water = sum(float(c["surface_water_kg"]) for c in matter["cells"])
    soil_water = sum(float(c["soil_water_kg"]) for c in matter["cells"])

    return {
        "environment": {
            "mean_temperature": round(sum(temperatures) / len(temperatures), 10),
            "surface_water_kg": round(surface_water, 10),
            "soil_water_kg": round(soil_water, 10),
        },
        "ecology": ecology_metrics(producers, consumers),
        "population": population_metrics(humans),
        "emergence": classify_emergence(humans),
    }
