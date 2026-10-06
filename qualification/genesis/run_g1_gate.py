from __future__ import annotations

from hrm_genesis import GenesisConfig, GenesisSimulation


def mean(world: dict, field: str) -> float:
    return sum(float(c[field]) for c in world["cells"]) / len(world["cells"])


def signature(sim: GenesisSimulation):
    return sim.snapshot().ledger_digest, sim.world_state()


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

    quarter = max(1, config.ticks_per_year // 4)
    a.run(quarter)
    quarter_world = a.world_state()

    a.run(ten_year_ticks - 1 - quarter)
    b = GenesisSimulation(config)
    b.run(ten_year_ticks)

    checks = {
        "ten_year_epoch": a.snapshot().epoch == ten_year_ticks,
        "deterministic_climate_run": signature(a) == signature(b),
        "ledger_valid": a.ledger.verify_chain() and b.ledger.verify_chain(),
        "seasonal_temperature_changes": first_temp != mean(quarter_world, "temperature"),
        "seasonal_solar_changes": first_solar != mean(quarter_world, "solar"),
        "precipitation_occurs": any(float(c["precipitation"]) > 0 for c in a.world_state()["cells"]),
        "world_has_no_matter_inventory": all(
            "surface_water_kg" not in c and "elements_kg" not in c
            for c in a.world_state()["cells"]
        ),
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
