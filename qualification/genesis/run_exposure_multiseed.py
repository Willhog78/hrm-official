"""Bounded multi-seed PR39 weather-survival attribution, no scripted behavior."""
from __future__ import annotations
from collections import Counter
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.matter.pools import total_water
from hrm_genesis.ecology.animals import consumer_water_total_kg
from hrm_genesis.human.biology import human_water_total_kg

SEEDS = ("exposure-a", "exposure-b", "exposure-c", "exposure-d")
DAYS = 90

def run(seed, weather):
    config = GenesisConfig(
        master_seed=seed, world_width=4, world_height=4, ticks_per_year=365,
        material_scale_factor=1000.0,
        producer_ecology_enabled=True, consumer_ecology_enabled=True,
        human_biology_enabled=True, human_cognition_enabled=True,
        human_actions_enabled=True, human_calibration_enabled=True,
        agentus_capacities_enabled=True, genesis_wind_enabled=weather,
        agentus_subcell_position_enabled=weather,
    )
    sim = GenesisSimulation(config)
    maximum_error = 0.0
    total_cold = total_heat = total_wet = 0.0
    first_extinction = None
    for day in range(1, DAYS + 1):
        sim.run(1)
        humans = sim.human_state()
        m = sim.matter_state()
        water = total_water(m["cells"]) + consumer_water_total_kg(sim.consumer_state()) + human_water_total_kg(humans)
        expected = m["initial_water_kg"] + m["water_input_kg"] - m["water_output_kg"]
        maximum_error = max(maximum_error, abs(water - expected))
        total_cold += sum(float(h.get("cold_exposure", 0)) for h in humans["humans"])
        total_heat += sum(float(h.get("heat_exposure", 0)) for h in humans["humans"])
        total_wet += sum(float(h.get("skin_wetness", 0)) for h in humans["humans"])
        if not humans["humans"] and first_extinction is None:
            first_extinction = day
    h = sim.human_state()
    counts = dict(sorted(h.get("cumulative_deaths_by_cause", {}).items()))
    print(f"RESULT seed={seed} weather={int(weather)} alive={len(h['humans'])} deaths={counts} "
          f"extinct_day={first_extinction} cumulative_cold={total_cold:.3f} "
          f"cumulative_heat={total_heat:.3f} cumulative_wet={total_wet:.3f} "
          f"water_error_kg={maximum_error:.9f}", flush=True)
    assert sim.ledger.verify_chain(), "ledger integrity failure"
    if weather:
        assert maximum_error < 1e-5, f"weather conservation failure seed={seed}: {maximum_error}"
    return counts

def main():
    for seed in SEEDS:
        run(seed, False)
        run(seed, True)
    print("MULTISEED_ATTRIBUTION_COMPLETE", flush=True)

if __name__ == "__main__":
    main()
