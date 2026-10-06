from __future__ import annotations

from pathlib import Path

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.autonomy import (
    dynamic_span,
    ecology_snapshot,
    occupied_consumer_cells,
    occupied_producer_cells,
)
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.ecology.plants import ecology_element_totals
from hrm_genesis.matter.pools import total_elements, total_water
from qualification.genesis.scenarios.g4_stress import drought_then_recovery


def combined_element_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    m = total_elements(matter["cells"])
    p = ecology_element_totals(sim.ecology_state())
    a = consumer_element_totals(sim.consumer_state())
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial) | set(m) | set(p) | set(a))
    return {
        s: m.get(s, 0.0) + p.get(s, 0.0) + a.get(s, 0.0) - initial.get(s, 0.0)
        for s in symbols
    }


def combined_water_error(sim: GenesisSimulation) -> float:
    matter = sim.matter_state()
    stored = total_water(matter["cells"]) + consumer_water_total_kg(sim.consumer_state())
    expected = (
        float(matter["initial_water_kg"])
        + float(matter["water_input_kg"])
        - float(matter["water_output_kg"])
    )
    return stored - expected


def test_g4_one_hundred_year_zero_intervention_run():
    config = GenesisConfig(
        master_seed="g4-century",
        world_width=4,
        world_height=4,
        ticks_per_year=12,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
    )
    sim = GenesisSimulation(config)
    samples = []

    for _ in range(100):
        sim.run(config.ticks_per_year)
        samples.append(ecology_snapshot(sim.ecology_state(), sim.consumer_state()))

    assert sim.snapshot().epoch == 100 * config.ticks_per_year
    assert sim.ledger.verify_chain()
    assert all(abs(v) < 5e-5 for v in combined_element_errors(sim).values())
    assert abs(combined_water_error(sim)) < 5e-5
    assert dynamic_span(samples, "producer_biomass_kg") > 0.0


def test_g4_migration_changes_occupied_consumer_cells():
    sim = GenesisSimulation(
        GenesisConfig(
            master_seed="g4-migration",
            world_width=6,
            world_height=6,
            ticks_per_year=24,
            producer_ecology_enabled=True,
            consumer_ecology_enabled=True,
        )
    )
    before = occupied_consumer_cells(sim.consumer_state())
    sim.run(40)
    after = occupied_consumer_cells(sim.consumer_state())
    assert before != after


def test_g4_controlled_drought_causes_local_loss_and_recovery():
    sim = GenesisSimulation(
        GenesisConfig(
            master_seed="g4-stress",
            world_width=6,
            world_height=4,
            ticks_per_year=24,
            producer_ecology_enabled=True,
            consumer_ecology_enabled=True,
        )
    )
    result = drought_then_recovery(
        producer_state=sim.ecology_state(),
        consumer_state=sim.consumer_state(),
        matter_state=sim.matter_state(),
        world_state=sim.world_state(),
        drought_ticks=60,
        recovery_ticks=120,
    )
    assert result["drought_left"] < result["before_left"]
    assert result["recovered_left"] > result["drought_left"]
    assert result["drought_right"] > 0.0


def test_g4_checkpoint_resume_matches_century_tail(tmp_path: Path):
    config = GenesisConfig(
        master_seed="g4-checkpoint",
        world_width=4,
        world_height=4,
        ticks_per_year=12,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
    )
    total = 100 * config.ticks_per_year
    split_at = 50 * config.ticks_per_year

    direct = GenesisSimulation(config)
    direct.run(total)

    split = GenesisSimulation(config)
    split.run(split_at)
    path = tmp_path / "g4-century.json"
    split.write_checkpoint(path)
    resumed = GenesisSimulation.load_checkpoint(path, config)
    resumed.run(total - split_at)

    assert resumed.snapshot().ledger_digest == direct.snapshot().ledger_digest
    assert resumed.world_state() == direct.world_state()
    assert resumed.matter_state() == direct.matter_state()
    assert resumed.ecology_state() == direct.ecology_state()
    assert resumed.consumer_state() == direct.consumer_state()
