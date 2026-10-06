from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.plants import (
    ecology_element_totals,
    evolve_producers,
    producer_biomass_kg,
    producer_detritus_mass_kg,
    producer_seed_mass_kg,
)
from hrm_genesis.matter.accounting import water_balance_error
from hrm_genesis.matter.pools import total_elements


def signature(sim: GenesisSimulation):
    snap = sim.snapshot()
    return (
        snap.epoch,
        snap.ledger_digest,
        sim.world_state(),
        sim.matter_state(),
        sim.ecology_state(),
    )


def combined_element_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    ecology = sim.ecology_state()
    m = total_elements(matter["cells"])
    e = ecology_element_totals(ecology)
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial) | set(m) | set(e))
    return {
        s: m.get(s, 0.0) + e.get(s, 0.0) - initial.get(s, 0.0)
        for s in symbols
    }


def test_g2_initial_biomass_is_debited_from_matter():
    sim = GenesisSimulation(
        GenesisConfig(master_seed="g2-genesis", producer_ecology_enabled=True)
    )
    assert producer_biomass_kg(sim.ecology_state()) > 0.0
    errors = combined_element_errors(sim)
    assert all(abs(v) < 1e-6 for v in errors.values())


def test_g2_growth_reproduction_death_and_decomposition_are_materially_accounted():
    config = GenesisConfig(
        master_seed="g2-cycles",
        world_width=5,
        world_height=5,
        ticks_per_year=36,
        producer_ecology_enabled=True,
    )
    sim = GenesisSimulation(config)
    initial_biomass = producer_biomass_kg(sim.ecology_state())
    sim.run(config.ticks_per_year * 4)

    ecology = sim.ecology_state()
    assert producer_biomass_kg(ecology) != initial_biomass
    assert producer_seed_mass_kg(ecology) > 0.0
    assert producer_detritus_mass_kg(ecology) > 0.0

    errors = combined_element_errors(sim)
    assert all(abs(v) < 1e-5 for v in errors.values())
    assert abs(water_balance_error(sim.matter_state())) < 1e-5


def test_g2_ten_year_run_is_deterministic():
    config = GenesisConfig(
        master_seed="g2-determinism",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
        producer_ecology_enabled=True,
    )
    ticks = config.ticks_per_year * 10
    a = GenesisSimulation(config)
    b = GenesisSimulation(config)
    a.run(ticks)
    b.run(ticks)
    assert signature(a) == signature(b)
    assert a.ledger.verify_chain()
    assert b.ledger.verify_chain()


def test_g2_checkpoint_restore_reproduces_biosphere(tmp_path: Path):
    config = GenesisConfig(
        master_seed="g2-checkpoint",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
        producer_ecology_enabled=True,
    )
    total = 120

    direct = GenesisSimulation(config)
    direct.run(total)

    split = GenesisSimulation(config)
    split.run(41)
    path = tmp_path / "g2.json"
    split.write_checkpoint(path)
    resumed = GenesisSimulation.load_checkpoint(path, config)
    resumed.run(total - 41)

    assert signature(resumed) == signature(direct)


def test_g2_no_light_causes_biomass_collapse_without_rescue():
    sim = GenesisSimulation(
        GenesisConfig(
            master_seed="g2-dark",
            world_width=4,
            world_height=4,
            producer_ecology_enabled=True,
        )
    )
    ecology = sim.ecology_state()
    matter = sim.matter_state()
    world = deepcopy(sim.world_state())
    start = producer_biomass_kg(ecology)

    for cell in world["cells"]:
        cell["solar"] = 0.0
        cell["temperature"] = 20.0
        cell["precipitation"] = 0.0

    for epoch in range(80):
        ecology, matter = evolve_producers(ecology, matter, world, epoch)

    assert producer_biomass_kg(ecology) < start * 0.02


def test_g2_no_water_causes_biomass_collapse_without_rescue():
    sim = GenesisSimulation(
        GenesisConfig(
            master_seed="g2-dry",
            world_width=4,
            world_height=4,
            producer_ecology_enabled=True,
        )
    )
    ecology = sim.ecology_state()
    matter = deepcopy(sim.matter_state())
    world = deepcopy(sim.world_state())
    start = producer_biomass_kg(ecology)

    for cell in matter["cells"]:
        cell["surface_water_kg"] = 0.0
        cell["soil_water_kg"] = 0.0
    for cell in world["cells"]:
        cell["solar"] = 1.0
        cell["temperature"] = 22.0
        cell["precipitation"] = 0.0

    for epoch in range(80):
        ecology, matter = evolve_producers(ecology, matter, world, epoch)

    assert producer_biomass_kg(ecology) < start * 0.02
