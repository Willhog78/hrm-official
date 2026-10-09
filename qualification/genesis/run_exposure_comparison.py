"""Finite comparative exposure diagnostic, without scripted Agentus actions."""
from __future__ import annotations

import argparse
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.matter.pools import total_water
from hrm_genesis.ecology.animals import consumer_water_total_kg
from hrm_genesis.human.biology import human_water_total_kg


def inventory_error(sim):
    m = sim.matter_state()
    stored = total_water(m["cells"]) + consumer_water_total_kg(sim.consumer_state()) + human_water_total_kg(sim.human_state())
    return stored - (m["initial_water_kg"] + m["water_input_kg"] - m["water_output_kg"])


def run(weather, days):
    cfg = GenesisConfig(
        master_seed="pr39-exposure-30-day-comparison", world_width=4, world_height=4,
        ticks_per_year=365, material_scale_factor=1000.0,
        producer_ecology_enabled=True, consumer_ecology_enabled=True,
        human_biology_enabled=True, human_cognition_enabled=True,
        human_actions_enabled=True, human_calibration_enabled=True,
        agentus_capacities_enabled=True, genesis_wind_enabled=weather,
        agentus_subcell_position_enabled=weather,
    )
    sim = GenesisSimulation(cfg)
    largest_error = abs(inventory_error(sim))
    for day in range(1, days + 1):
        if weather and day >= 29:
            mm = sim.matter_state()
            print(f"PRE_DAY={day} MATTER={total_water(mm['cells']):.6f} IN={mm['water_input_kg']:.6f} OUT={mm['water_output_kg']:.6f} ANIMAL={consumer_water_total_kg(sim.consumer_state()):.6f} HUMAN={human_water_total_kg(sim.human_state()):.6f} ANIMALS={len(sim.consumer_state()['animals'])} HUMANS={len(sim.human_state()['humans'])}", flush=True)
        sim.run(1)
        if weather and day >= 29:
            mm = sim.matter_state()
            print(f"POST_DAY={day} MATTER={total_water(mm['cells']):.6f} IN={mm['water_input_kg']:.6f} OUT={mm['water_output_kg']:.6f} ANIMAL={consumer_water_total_kg(sim.consumer_state()):.6f} HUMAN={human_water_total_kg(sim.human_state()):.6f} ANIMALS={len(sim.consumer_state()['animals'])} HUMANS={len(sim.human_state()['humans'])}", flush=True)
        error = inventory_error(sim)
        largest_error = max(largest_error, abs(error))
        if weather and abs(error) > 1e-5:
            print(f"BALANCE_DAY={day} DELTA_KG={error:.9f}", flush=True)
        if day % 10 == 0 or day == days:
            h = sim.human_state()["humans"]
            w = sim.world_state()["cells"]
            m = sim.matter_state()["cells"]
            print(
                f"DAY={day} WEATHER={int(weather)} ALIVE={len(h)} "
                f"WET={sum(x.get('skin_wetness', 0) for x in h):.4f} "
                f"COLD={sum(x.get('cold_exposure', 0) for x in h):.4f} "
                f"HEAT={sum(x.get('heat_exposure', 0) for x in h):.4f} "
                f"INJURY={sum(x.get('injury', 0) for x in h):.4f} "
                f"SNOW_KG={sum(x.get('snow_water_kg', 0) for x in m):.5f} "
                f"MAX_WIND={max(x.get('wind_speed_m_s', 0) for x in w):.3f}",
                flush=True
            )
    print(f"WEATHER={int(weather)} WATER_MAX_ERROR_KG={largest_error:.9f}", flush=True)
    assert largest_error < 1e-5, "whole-domain water not conserved"
    assert sim.ledger.verify_chain(), "ledger chain invalid"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    for mode in (False, True):
        run(mode, args.days)
    print("COMPARATIVE_EXPOSURE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
