from __future__ import annotations

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.ecology.plants import ecology_element_totals
from hrm_genesis.ecology.populations import living_population, population_counts
from hrm_genesis.matter.pools import total_elements, total_water


def combined_element_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    m = total_elements(matter["cells"])
    p = ecology_element_totals(sim.ecology_state())
    a = consumer_element_totals(sim.consumer_state())
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial) | set(m) | set(p) | set(a))
    return {s: m.get(s,0.0)+p.get(s,0.0)+a.get(s,0.0)-initial.get(s,0.0) for s in symbols}


def combined_water_error(sim: GenesisSimulation) -> float:
    matter = sim.matter_state()
    stored = total_water(matter["cells"]) + consumer_water_total_kg(sim.consumer_state())
    expected = float(matter["initial_water_kg"]) + float(matter["water_input_kg"]) - float(matter["water_output_kg"])
    return stored - expected


def signature(sim: GenesisSimulation):
    return (
        sim.snapshot().ledger_digest,
        sim.world_state(),
        sim.matter_state(),
        sim.ecology_state(),
        sim.consumer_state(),
    )


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g3-gate",
        world_width=6,
        world_height=6,
        ticks_per_year=48,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
    )
    ticks = 120
    a = GenesisSimulation(config)
    initial = population_counts(a.consumer_state())
    b = GenesisSimulation(config)
    a.run(ticks)
    b.run(ticks)
    final = population_counts(a.consumer_state())

    checks = {
        "deterministic_consumer_run": signature(a) == signature(b),
        "ledger_valid": a.ledger.verify_chain() and b.ledger.verify_chain(),
        "two_initial_populations": initial.get("grazer",0) > 0 and initial.get("browser",0) > 0,
        "grazer_persists": final.get("grazer",0) > 0,
        "browser_persists": final.get("browser",0) > 0,
        "element_conservation": all(abs(v) < 2e-5 for v in combined_element_errors(a).values()),
        "water_accounting": abs(combined_water_error(a)) < 2e-5,
        "no_human_state": not any(aid.startswith("human.") for aid in a.fabric.authority_ids),
    }

    failed = [k for k,v in checks.items() if not v]
    for k,v in checks.items():
        print(f"{k}: {'PASS' if v else 'FAIL'}")
    if failed:
        print("G3_GATE_FAIL:", ", ".join(failed))
        return 1
    print("G3_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
