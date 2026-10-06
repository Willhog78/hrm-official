from __future__ import annotations

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.world.state import nutrient_balance_error, water_balance_error


def mean(world: dict, field: str) -> float:
    return sum(float(c[field]) for c in world["cells"]) / len(world["cells"])


def signature(sim: GenesisSimulation):
    state = sim.world_state()
    return sim.snapshot().ledger_digest, state


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g1-gate",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
    )
    ten_year_ticks = config.ticks_per_year * 10

    a = GenesisSimulation(config)
    a.run(1)
    first = a.world_state()
    first_temp = mean(first, "temperature")
    first_solar = mean(first, "solar")
    a.run(ten_year_ticks - 1)
    final = a.world_state()

    b = GenesisSimulation(config)
    b.run(ten_year_ticks)

    checks = {
        "ten_year_epoch": a.snapshot().epoch == ten_year_ticks,
        "deterministic_ten_year_run": signature(a) == signature(b),
        "ledger_valid": a.ledger.verify_chain() and b.ledger.verify_chain(),
        "seasonal_temperature_changes": first_temp != mean(final, "temperature"),
        "seasonal_solar_changes": first_solar != mean(final, "solar"),
        "precipitation_entered_system": float(final["water_input"]) > 0.0,
        "evaporation_left_system": float(final["water_output"]) > 0.0,
        "water_accounting": abs(water_balance_error(final)) < 1e-5,
        "nutrient_conservation": abs(nutrient_balance_error(final)) < 1e-5,
        "no_organism_state": set(a.fabric.authority_ids) == {"genesis.system", "world.environment"},
    }

    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if failed:
        print("G1_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G1_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
