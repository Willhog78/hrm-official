from __future__ import annotations

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.plants import (
    ecology_element_totals,
    producer_biomass_kg,
    producer_detritus_mass_kg,
    producer_seed_mass_kg,
)
from hrm_genesis.matter.accounting import water_balance_error
from hrm_genesis.matter.pools import total_elements


def combined_element_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    ecology = sim.ecology_state()
    m = total_elements(matter["cells"])
    e = ecology_element_totals(ecology)
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial) | set(m) | set(e))
    return {s: m.get(s, 0.0) + e.get(s, 0.0) - initial.get(s, 0.0) for s in symbols}


def signature(sim: GenesisSimulation):
    return (
        sim.snapshot().ledger_digest,
        sim.world_state(),
        sim.matter_state(),
        sim.ecology_state(),
    )


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g2-gate",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
        producer_ecology_enabled=True,
    )
    ticks = config.ticks_per_year * 10

    a = GenesisSimulation(config)
    initial_biomass = producer_biomass_kg(a.ecology_state())
    b = GenesisSimulation(config)
    a.run(ticks)
    b.run(ticks)

    ecology = a.ecology_state()
    checks = {
        "ten_year_epoch": a.snapshot().epoch == ticks,
        "deterministic_biosphere": signature(a) == signature(b),
        "ledger_valid": a.ledger.verify_chain() and b.ledger.verify_chain(),
        "producer_state_exists": initial_biomass > 0.0,
        "biomass_is_dynamic": producer_biomass_kg(ecology) != initial_biomass,
        "reproduction_occurred": producer_seed_mass_kg(ecology) > 0.0,
        "death_occurred": producer_detritus_mass_kg(ecology) > 0.0,
        "element_conservation": all(
            abs(v) < 1e-5 for v in combined_element_errors(a).values()
        ),
        "water_accounting": abs(water_balance_error(a.matter_state())) < 1e-5,
        "no_consumers_or_humans": not any(
            aid.startswith("ecology.consumers") or aid.startswith("human.")
            for aid in a.fabric.authority_ids
        ),
    }

    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if failed:
        print("G2_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G2_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
