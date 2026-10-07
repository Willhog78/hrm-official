from __future__ import annotations

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.plants import ecology_element_totals, producer_biomass_kg
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.human import human_element_totals, human_water_total_kg
from hrm_genesis.human.regions import POPULATION_IDS, resource_profile
from hrm_genesis.matter.pools import total_elements, total_water


def combined_element_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    pools = [
        total_elements(matter["cells"]),
        ecology_element_totals(sim.ecology_state()),
        consumer_element_totals(sim.consumer_state()),
        human_element_totals(sim.human_state()),
    ]
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial).union(*(set(p) for p in pools)))
    return {
        symbol: sum(pool.get(symbol, 0.0) for pool in pools) - initial.get(symbol, 0.0)
        for symbol in symbols
    }


def combined_water_error(sim: GenesisSimulation) -> float:
    matter = sim.matter_state()
    stored = (
        total_water(matter["cells"])
        + consumer_water_total_kg(sim.consumer_state())
        + human_water_total_kg(sim.human_state())
    )
    expected = (
        float(matter["initial_water_kg"])
        + float(matter["water_input_kg"])
        - float(matter["water_output_kg"])
    )
    return stored - expected


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g10-1-scale-substrate",
        world_width=32,
        world_height=32,
        ticks_per_year=12,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_cognition_enabled=True,
        human_actions_enabled=True,
        multi_population_enabled=True,
        material_scale_factor=1000.0,
    )
    sim = GenesisSimulation(config)

    initial_biomass = producer_biomass_kg(sim.ecology_state())
    initial_water = float(sim.matter_state()["initial_water_kg"])
    profiles = {
        pid: resource_profile(pid, sim.ecology_state(), sim.matter_state())
        for pid in POPULATION_IDS
    }

    # Reserve criterion: before adult anatomy is enabled, each founder region
    # must already contain far more than two 70 kg bodies worth of local plant
    # biomass and water. This proves the substrate, not human physiology.
    regional_reserve = all(
        profile["mean_food_kg"] * 256.0 >= 140.0
        and profile["mean_water_kg"] * 256.0 >= 84.0
        for profile in profiles.values()
    )

    sim.run(24)

    errors = combined_element_errors(sim)
    checks = {
        "expanded_world_32x32": sim.config.world_width == 32 and sim.config.world_height == 32,
        "scaled_material_regime_enabled": sim.config.material_scale_factor == 1000.0,
        "producer_biomass_is_human_scale_capable": initial_biomass >= 1000.0,
        "water_inventory_is_human_scale_capable": initial_water >= 1000000.0,
        "each_population_region_has_adult_scale_reserve": regional_reserve,
        "humans_still_present": len(sim.human_state()["humans"]) > 0,
        "consumers_still_present": len(sim.consumer_state()["animals"]) > 0,
        "plants_still_present": producer_biomass_kg(sim.ecology_state()) > 0.0,
        "element_conservation": all(abs(v) < 5e-3 for v in errors.values()),
        "water_accounting": abs(combined_water_error(sim)) < 5e-3,
        "ledger_valid": sim.ledger.verify_chain(),
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print("G10_1_INITIAL_BIOMASS_KG:", initial_biomass)
    print("G10_1_INITIAL_WATER_KG:", initial_water)
    print("G10_1_REGION_PROFILES:", profiles)
    print("G10_1_MAX_ELEMENT_ERROR_KG:", max(abs(v) for v in errors.values()))
    print("G10_1_WATER_ERROR_KG:", combined_water_error(sim))

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G10_1_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G10_1_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
