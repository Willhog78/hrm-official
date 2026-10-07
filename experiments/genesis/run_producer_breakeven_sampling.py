"""Observer-only: per-cell producer net rate implied by plants.py constants.

Runs seed A without Agentus and every 30 days (second year) reports how many
cells have a positive net per-unit-biomass rate:
growth(condition) - mortality(stress) - seed shedding. Old-age mortality is
omitted because germination keeps cell ages near zero (see food intake
diagnosis). Nothing is written back to the simulation.
"""
from __future__ import annotations

from dataclasses import replace

from hrm_genesis import GenesisSimulation
from hrm_genesis.ecology import plants

from experiments.genesis.run_agentus_food_intake_diagnosis import _config


def main() -> int:
    config = replace(
        _config("agentus-demography-a"),
        human_biology_enabled=False,
        human_cognition_enabled=False,
        human_actions_enabled=False,
        multi_population_enabled=False,
        human_calibration_enabled=False,
    )
    sim = GenesisSimulation(config)
    for day in range(730):
        sim.run(1)
        if day < 360 or day % 30:
            continue
        world = {(c["x"], c["y"]): c for c in sim.world_state()["cells"]}
        matter = {(c["x"], c["y"]): c for c in sim.matter_state()["cells"]}
        rates = []
        limiter = {"light": 0, "temperature": 0, "water": 0}
        for xy in world:
            light, temp, water = plants._environment_factors(world[xy], matter[xy])
            condition = min(light, temp, water)
            limiter[min((("light", light), ("temperature", temp), ("water", water)), key=lambda kv: kv[1])[0]] += 1
            rates.append(
                plants.BASE_GROWTH_FRACTION * condition
                - (plants.BASE_MORTALITY_FRACTION + 0.08 * (1.0 - condition))
                - (plants.REPRODUCTION_FRACTION if condition >= 0.5 else 0.0)
            )
        print(
            f"day={day} year_day={day % 365} cells_net_positive={sum(r > 0 for r in rates)}"
            f" mean_rate={sum(rates) / len(rates):.4f} max_rate={max(rates):.4f} limiter={limiter}",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
