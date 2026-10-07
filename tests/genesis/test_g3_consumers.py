from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.traits import trait_for
from hrm_genesis.ecology.animals import (
    consumer_element_totals,
    consumer_water_total_kg,
    evolve_consumers,
)
from hrm_genesis.ecology.plants import ecology_element_totals
from hrm_genesis.ecology.populations import living_population, population_counts
from hrm_genesis.matter.pools import total_elements, total_water


def signature(sim: GenesisSimulation):
    snap = sim.snapshot()
    return (
        snap.epoch,
        snap.ledger_digest,
        sim.world_state(),
        sim.matter_state(),
        sim.ecology_state(),
        sim.consumer_state(),
    )


def combined_element_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    producers = sim.ecology_state()
    consumers = sim.consumer_state()
    m = total_elements(matter["cells"])
    p = ecology_element_totals(producers)
    a = consumer_element_totals(consumers)
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


def test_g3_two_consumer_populations_exist_and_are_materially_seeded():
    sim = GenesisSimulation(
        GenesisConfig(
            master_seed="g3-genesis",
            consumer_ecology_enabled=True,
            producer_ecology_enabled=True,
        )
    )
    counts = population_counts(sim.consumer_state())
    assert counts.get("grazer", 0) > 0
    assert counts.get("browser", 0) > 0
    assert all(abs(v) < 1e-6 for v in combined_element_errors(sim).values())
    assert abs(combined_water_error(sim)) < 1e-6


def test_g3_consumers_move_feed_drink_age_and_learn():
    sim = GenesisSimulation(
        GenesisConfig(
            master_seed="g3-behavior",
            world_width=5,
            world_height=5,
            ticks_per_year=36,
            producer_ecology_enabled=True,
            consumer_ecology_enabled=True,
        )
    )
    before = {a["id"]: deepcopy(a) for a in sim.consumer_state()["animals"]}
    sim.run(30)
    after = {a["id"]: a for a in sim.consumer_state()["animals"]}

    shared = sorted(set(before) & set(after))
    assert shared
    assert any(
        (after[i]["x"], after[i]["y"]) != (before[i]["x"], before[i]["y"])
        or after[i]["age_ticks"] > before[i]["age_ticks"]
        for i in shared
    )
    assert any(after[i]["forage_bias"] != before[i]["forage_bias"] for i in shared)


def test_g3_long_run_preserves_elements_and_water_accounting():
    config = GenesisConfig(
        master_seed="g3-conservation",
        world_width=5,
        world_height=5,
        ticks_per_year=36,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
    )
    sim = GenesisSimulation(config)
    sim.run(config.ticks_per_year * 4)

    assert all(abs(v) < 2e-5 for v in combined_element_errors(sim).values())
    assert abs(combined_water_error(sim)) < 2e-5


def test_g3_favorable_seed_keeps_both_populations_present():
    config = GenesisConfig(
        master_seed="g3-persist",
        world_width=6,
        world_height=6,
        ticks_per_year=48,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
    )
    sim = GenesisSimulation(config)
    sim.run(120)
    assert living_population(sim.consumer_state(), "grazer") > 0
    assert living_population(sim.consumer_state(), "browser") > 0


def test_g3_no_food_causes_consumer_collapse():
    sim = GenesisSimulation(
        GenesisConfig(
            master_seed="g3-starve",
            world_width=4,
            world_height=4,
            producer_ecology_enabled=True,
            consumer_ecology_enabled=True,
        )
    )
    consumers = sim.consumer_state()
    producers = deepcopy(sim.ecology_state())
    matter = sim.matter_state()
    world = sim.world_state()

    for cell in producers["cells"]:
        for symbol in cell["plant_elements_kg"]:
            cell["plant_elements_kg"][symbol] = 0.0
            cell["seed_elements_kg"][symbol] = 0.0

    # Herbivores starve first. A predator can outlive them on the energy of its
    # last kill (fallible predation postdates this test), so collapse of the
    # whole community is checked over a longer horizon.
    for epoch in range(300):
        consumers, producers, matter = evolve_consumers(
            consumers, producers, matter, world, epoch
        )
        if epoch == 99:
            assert not any(
                trait_for(str(a["species"])).trophic_role == "herbivore"
                for a in consumers["animals"]
            )

    assert living_population(consumers) == 0


def test_g3_checkpoint_restore_reproduces_consumers(tmp_path: Path):
    config = GenesisConfig(
        master_seed="g3-checkpoint",
        world_width=5,
        world_height=5,
        ticks_per_year=36,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
    )
    total = 90

    direct = GenesisSimulation(config)
    direct.run(total)

    split = GenesisSimulation(config)
    split.run(31)
    path = tmp_path / "g3.json"
    split.write_checkpoint(path)
    resumed = GenesisSimulation.load_checkpoint(path, config)
    resumed.run(total - 31)

    assert signature(resumed) == signature(direct)
    assert resumed.ledger.verify_chain()
