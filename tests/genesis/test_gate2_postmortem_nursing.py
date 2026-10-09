"""Regression: a deceased caregiver cannot provision dependents after burial of body water."""
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.matter.pools import total_water
from hrm_genesis.ecology.animals import consumer_water_total_kg
from hrm_genesis.human.biology import human_water_total_kg


def test_weather_run_conserves_water_during_caregiver_death():
    config = GenesisConfig(
        master_seed="pr39-exposure-30-day-comparison", world_width=4, world_height=4,
        ticks_per_year=365, material_scale_factor=1000.0,
        producer_ecology_enabled=True, consumer_ecology_enabled=True,
        human_biology_enabled=True, human_cognition_enabled=True,
        human_actions_enabled=True, human_calibration_enabled=True,
        agentus_capacities_enabled=True, genesis_wind_enabled=True,
        agentus_subcell_position_enabled=True,
    )
    sim = GenesisSimulation(config)
    for day in range(1, 31):
        sim.run(1)
        matter = sim.matter_state()
        water = (total_water(matter["cells"]) +
                 consumer_water_total_kg(sim.consumer_state()) +
                 human_water_total_kg(sim.human_state()))
        expected = (matter["initial_water_kg"] + matter["water_input_kg"] -
                    matter["water_output_kg"])
        assert abs(water - expected) < 1e-5, f"day={day}, error={water-expected}"
    assert sim.human_state()["cumulative_deaths"] >= 1
