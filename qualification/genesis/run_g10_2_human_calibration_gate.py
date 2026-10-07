from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.ecology.plants import ecology_element_totals
from hrm_genesis.human import human_element_totals, human_water_total_kg
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


def total_mass(human: dict) -> float:
    return sum(float(v) for v in human["body_elements_kg"].values()) + float(human["body_water_kg"])


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g10-2-human-calibration",
        world_width=32,
        world_height=32,
        ticks_per_year=365,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_cognition_enabled=True,
        human_actions_enabled=True,
        multi_population_enabled=True,
        material_scale_factor=1000.0,
        human_calibration_enabled=True,
    )

    direct = GenesisSimulation(config)
    initial = direct.human_state()
    profile = initial["physiology_profile"]
    masses = [total_mass(h) for h in initial["humans"]]
    water_fractions = [
        float(h["body_water_kg"]) / total_mass(h)
        for h in initial["humans"]
        if total_mass(h) > 0
    ]

    direct.run(30)
    final = direct.human_state()

    with TemporaryDirectory() as td:
        checkpoint = Path(td) / "g10-2-checkpoint.json"
        resumed = GenesisSimulation(config)
        resumed.run(15)
        resumed.write_checkpoint(checkpoint)
        resumed = GenesisSimulation.load_checkpoint(checkpoint, config)
        resumed.run(15)

        checks = {
            "calibrated_mode_enabled": bool(profile["calibrated"]),
            "daily_timebase": config.ticks_per_year == 365,
            "eight_founders_materialized": len(initial["humans"]) == 8,
            "reference_total_mass_70kg": all(abs(m - 70.0) < 1e-6 for m in masses),
            "reference_body_water_42kg": all(abs(float(h["body_water_kg"]) - 42.0) < 1e-6 for h in initial["humans"]),
            "reference_water_fraction_60pct": all(abs(v - 0.60) < 1e-6 for v in water_fractions),
            "maturity_is_18_years": int(profile["maturity_ticks"]) == 18 * 365,
            "max_age_is_90_years": int(profile["max_age_ticks"]) == 90 * 365,
            "reproduction_cooldown_is_one_year": int(profile["reproduction_cooldown_ticks"]) == 365,
            "daily_basal_energy_2000kcal": abs(float(profile["basal_energy_kcal_per_tick"]) - 2000.0) < 1e-9,
            "daily_water_turnover_2_5kg": abs(float(profile["water_loss_per_tick_kg"]) - 2.5) < 1e-9,
            "humans_survive_month_with_ecology": len(final["humans"]) > 0,
            "element_conservation": all(abs(v) < 5e-3 for v in combined_element_errors(direct).values()),
            "water_accounting": abs(combined_water_error(direct)) < 5e-3,
            "checkpoint_replay": (
                direct.matter_state() == resumed.matter_state()
                and direct.ecology_state() == resumed.ecology_state()
                and direct.consumer_state() == resumed.consumer_state()
                and direct.human_state() == resumed.human_state()
            ),
            "ledger_valid": direct.ledger.verify_chain() and resumed.ledger.verify_chain(),
        }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print("G10_2_INITIAL_MASSES_KG:", masses)
    print("G10_2_PROFILE:", profile)
    print("G10_2_FINAL_HUMANS:", len(final["humans"]))
    print("G10_2_MAX_ELEMENT_ERROR_KG:", max(abs(v) for v in combined_element_errors(direct).values()))
    print("G10_2_WATER_ERROR_KG:", combined_water_error(direct))

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G10_2_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G10_2_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
