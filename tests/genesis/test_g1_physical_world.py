from __future__ import annotations

from pathlib import Path

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.world.state import nutrient_balance_error, water_balance_error


def mean_field(world: dict, field: str) -> float:
    return sum(float(c[field]) for c in world["cells"]) / len(world["cells"])


def canonical_world(sim: GenesisSimulation):
    snap = sim.snapshot()
    return snap.epoch, snap.ledger_digest, sim.world_state()


def test_g1_grid_is_bounded_and_heterogeneous():
    config = GenesisConfig(
        master_seed="g1-grid",
        world_width=5,
        world_height=4,
        ticks_per_year=40,
    )
    sim = GenesisSimulation(config)
    world = sim.world_state()

    assert world["width"] == 5
    assert world["height"] == 4
    assert len(world["cells"]) == 20
    elevations = {float(c["elevation"]) for c in world["cells"]}
    nutrients = {float(c["nutrients"]) for c in world["cells"]}
    assert len(elevations) > 1
    assert len(nutrients) > 1


def test_g1_seasonality_changes_temperature_and_solar_input():
    config = GenesisConfig(
        master_seed="g1-season",
        world_width=4,
        world_height=4,
        ticks_per_year=40,
    )
    sim = GenesisSimulation(config)

    sim.run(1)
    early = sim.world_state()
    early_temp = mean_field(early, "temperature")
    early_solar = mean_field(early, "solar")

    sim.run(10)
    later = sim.world_state()
    later_temp = mean_field(later, "temperature")
    later_solar = mean_field(later, "solar")

    assert early_temp != later_temp
    assert early_solar != later_solar


def test_g1_water_and_nutrients_account_for_long_run():
    config = GenesisConfig(
        master_seed="g1-balance",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
    )
    sim = GenesisSimulation(config)
    sim.run(config.ticks_per_year * 10)
    world = sim.world_state()

    assert abs(water_balance_error(world)) < 1e-5
    assert abs(nutrient_balance_error(world)) < 1e-5
    assert float(world["water_input"]) > 0.0
    assert float(world["water_output"]) > 0.0


def test_g1_ten_year_run_is_deterministic():
    config = GenesisConfig(
        master_seed="g1-ten-years",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
    )
    a = GenesisSimulation(config)
    b = GenesisSimulation(config)

    ticks = config.ticks_per_year * 10
    a.run(ticks)
    b.run(ticks)

    assert canonical_world(a) == canonical_world(b)
    assert a.ledger.verify_chain()
    assert b.ledger.verify_chain()


def test_g1_checkpoint_restore_reproduces_world(tmp_path: Path):
    config = GenesisConfig(
        master_seed="g1-checkpoint",
        world_width=4,
        world_height=4,
        ticks_per_year=24,
    )
    total = config.ticks_per_year * 3

    direct = GenesisSimulation(config)
    direct.run(total)

    split = GenesisSimulation(config)
    split.run(17)
    path = tmp_path / "g1.json"
    split.write_checkpoint(path)
    resumed = GenesisSimulation.load_checkpoint(path, config)
    resumed.run(total - 17)

    assert canonical_world(resumed) == canonical_world(direct)
    assert resumed.ledger.verify_chain()
