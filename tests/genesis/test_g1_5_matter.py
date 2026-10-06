from __future__ import annotations

from pathlib import Path

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.matter import ELEMENTS
from hrm_genesis.matter.accounting import (
    element_balance_errors,
    hydrogen_oxygen_open_system_account,
    water_balance_error,
)


def signature(sim: GenesisSimulation):
    snap = sim.snapshot()
    return snap.epoch, snap.ledger_digest, sim.world_state(), sim.matter_state()


def test_g1_5_element_registry_contains_required_biological_and_material_elements():
    required = {"H", "C", "N", "O", "P", "S", "K", "Ca", "Mg", "Fe", "Si", "Cu", "Zn"}
    assert required <= set(ELEMENTS)
    assert all(ELEMENTS[s].atomic_number > 0 for s in required)
    assert all(ELEMENTS[s].atomic_mass_u > 0 for s in required)


def test_g1_5_world_and_matter_are_separate_authorities():
    sim = GenesisSimulation(GenesisConfig(master_seed="g1-5-authority"))
    assert set(sim.fabric.authority_ids) == {
        "genesis.system",
        "world.environment",
        "matter.environment",
    }
    assert "surface_water_kg" not in sim.world_state()["cells"][0]
    assert "elements_kg" in sim.matter_state()["cells"][0]


def test_g1_5_matter_is_heterogeneous_and_element_specific():
    sim = GenesisSimulation(
        GenesisConfig(master_seed="g1-5-elements", world_width=5, world_height=4)
    )
    matter = sim.matter_state()
    nitrogen = {float(c["elements_kg"]["N"]) for c in matter["cells"]}
    phosphorus = {float(c["elements_kg"]["P"]) for c in matter["cells"]}
    assert len(nitrogen) > 1
    assert len(phosphorus) > 1
    assert nitrogen != phosphorus


def test_g1_5_ten_year_conservation_and_open_water_account():
    config = GenesisConfig(
        master_seed="g1-5-balance",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
    )
    sim = GenesisSimulation(config)
    sim.run(config.ticks_per_year * 10)
    matter = sim.matter_state()

    assert abs(water_balance_error(matter)) < 1e-5
    errors = element_balance_errors(matter)
    assert all(abs(error) < 1e-5 for error in errors.values())
    assert float(matter["water_input_kg"]) > 0.0
    assert float(matter["water_output_kg"]) > 0.0

    ho = hydrogen_oxygen_open_system_account(matter)
    assert set(ho) == {"H_net_kg", "O_net_kg"}


def test_g1_5_ten_year_run_is_deterministic():
    config = GenesisConfig(
        master_seed="g1-5-determinism",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
    )
    ticks = config.ticks_per_year * 10
    a = GenesisSimulation(config)
    b = GenesisSimulation(config)
    a.run(ticks)
    b.run(ticks)
    assert signature(a) == signature(b)


def test_g1_5_checkpoint_restore_reproduces_matter(tmp_path: Path):
    config = GenesisConfig(
        master_seed="g1-5-checkpoint",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
    )
    total = 80

    direct = GenesisSimulation(config)
    direct.run(total)

    split = GenesisSimulation(config)
    split.run(29)
    path = tmp_path / "g1-5.json"
    split.write_checkpoint(path)
    resumed = GenesisSimulation.load_checkpoint(path, config)
    resumed.run(total - 29)

    assert signature(resumed) == signature(direct)
    assert resumed.ledger.verify_chain()
