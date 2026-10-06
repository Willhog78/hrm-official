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


def canonical_state(sim: GenesisSimulation) -> tuple[dict, dict, dict, dict]:
    return (
        sim.matter_state(),
        sim.ecology_state(),
        sim.consumer_state(),
        sim.human_state(),
    )


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g5-human-biology",
        world_width=4,
        world_height=4,
        ticks_per_year=12,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
    )

    direct = GenesisSimulation(config)
    initial_humans = direct.human_state()
    initial_ids = tuple(sorted(h["id"] for h in initial_humans["humans"]))
    initial_energy = sum(float(h["energy"]) for h in initial_humans["humans"])

    direct.run(24)
    final_humans = direct.human_state()
    final_energy = sum(float(h["energy"]) for h in final_humans["humans"])

    with TemporaryDirectory() as td:
        checkpoint = Path(td) / "g5-checkpoint.json"
        resumed = GenesisSimulation(config)
        resumed.run(12)
        resumed.write_checkpoint(checkpoint)
        resumed = GenesisSimulation.load_checkpoint(checkpoint, config)
        resumed.run(12)

        checks = {
            "human_authority_present": "human.biology" in direct.fabric.authority_ids,
            "initial_humans_materialized": len(initial_ids) == 2,
            "human_state_changed": final_humans != initial_humans and final_energy != initial_energy,
            "human_material_present": sum(human_element_totals(final_humans).values()) > 0.0,
            "human_water_present": human_water_total_kg(final_humans) > 0.0,
            "element_conservation": all(abs(v) < 5e-5 for v in combined_element_errors(direct).values()),
            "water_accounting": abs(combined_water_error(direct)) < 5e-5,
            "ledger_valid": direct.ledger.verify_chain(),
            "checkpoint_replay": canonical_state(direct) == canonical_state(resumed),
            "checkpoint_ledger_valid": resumed.ledger.verify_chain(),
            "no_cognition_state": not any(
                key in h
                for h in final_humans["humans"]
                for key in ("memory", "beliefs", "language", "plan", "profession", "culture")
            ),
        }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G5_GATE_FAIL:", ", ".join(failed))
        return 1

    print(
        "G5_RESULTS:",
        {
            "initial_humans": len(initial_ids),
            "final_humans": len(final_humans["humans"]),
            "ticks": 24,
            "max_abs_element_error_kg": max(abs(v) for v in combined_element_errors(direct).values()),
            "water_error_kg": combined_water_error(direct),
        },
    )
    print("G5_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
