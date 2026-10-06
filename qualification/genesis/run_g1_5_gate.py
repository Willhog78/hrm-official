from __future__ import annotations

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.matter.accounting import element_balance_errors, water_balance_error


def signature(sim: GenesisSimulation):
    return (
        sim.snapshot().ledger_digest,
        sim.world_state(),
        sim.matter_state(),
    )


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g1-5-gate",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
    )
    ticks = config.ticks_per_year * 10

    a = GenesisSimulation(config)
    b = GenesisSimulation(config)
    a.run(ticks)
    b.run(ticks)
    matter = a.matter_state()

    checks = {
        "ten_year_epoch": a.snapshot().epoch == ticks,
        "deterministic_replay": signature(a) == signature(b),
        "ledger_valid": a.ledger.verify_chain() and b.ledger.verify_chain(),
        "separate_authorities": set(a.fabric.authority_ids) == {
            "genesis.system",
            "world.environment",
            "matter.environment",
        },
        "water_input_exists": float(matter["water_input_kg"]) > 0.0,
        "water_output_exists": float(matter["water_output_kg"]) > 0.0,
        "water_accounting": abs(water_balance_error(matter)) < 1e-5,
        "element_conservation": all(
            abs(error) < 1e-5 for error in element_balance_errors(matter).values()
        ),
        "no_organism_state": not any(
            aid.startswith("ecology.") or aid.startswith("human.")
            for aid in a.fabric.authority_ids
        ),
    }

    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if failed:
        print("G1_5_GATE_FAIL:", ", ".join(failed))
        return 1
    print("G1_5_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
