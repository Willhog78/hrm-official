from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg
from hrm_genesis.ecology.plants import ecology_element_totals
from hrm_genesis.human import human_element_totals, human_water_total_kg
from hrm_genesis.human.biology import (
    HUMAN_MATURITY_TICKS,
    HUMAN_MAX_AGE_TICKS,
    _apply_physiology,
    evolve_humans,
)
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




def _plant_mass(cell: dict) -> float:
    return sum(float(v) for v in cell["plant_elements_kg"].values())


def focused_biology_checks(sim: GenesisSimulation) -> dict[str, bool]:
    # Birth: put the existing materially seeded adults together on one cell.
    # They still move and eat from real producer mass before reproduction, and
    # since PR #23 reproduction needs the pair together *after* movement. So
    # the probe uses a cell that stays the movement rule's choice for every
    # adult even after the earlier adults' bites; otherwise it would test
    # whether two uncognitive adults happen to stay together, not reproduction.
    humans = deepcopy(sim.human_state())
    producers = deepcopy(sim.ecology_state())
    matter = deepcopy(sim.matter_state())
    world = deepcopy(sim.world_state())

    bite = float(humans["physiology_profile"]["bite_cap_kg"])
    earlier_bites = bite * max(0, len(humans["humans"]) - 1)
    by_xy = {(int(c["x"]), int(c["y"])): c for c in producers["cells"]}

    def holds_the_pair(cell: dict) -> bool:
        x, y = int(cell["x"]), int(cell["y"])
        neighbours = [by_xy[n] for n in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)) if n in by_xy]
        return _plant_mass(cell) - earlier_bites > max((_plant_mass(n) for n in neighbours), default=0.0)

    stable = [cell for cell in producers["cells"] if holds_the_pair(cell)]
    if not stable:
        raise RuntimeError("G5 birth probe: no cell keeps the pair together under the movement rule")
    richest = max(stable, key=lambda cell: (_plant_mass(cell), -int(cell["y"]), -int(cell["x"])))
    xy = (int(richest["x"]), int(richest["y"]))
    for person in humans["humans"]:
        person["x"], person["y"] = xy
        person["age_ticks"] = HUMAN_MATURITY_TICKS + 1
        person["energy"] = 30.0
        person["last_reproduction_epoch"] = -1000000

    before_human_mass = sum(human_element_totals(humans).values())
    before_plant_mass = sum(
        _plant_mass(cell) + sum(float(v) for v in cell["detritus_elements_kg"].values())
        + sum(float(v) for v in cell["seed_elements_kg"].values())
        for cell in producers["cells"]
    )
    born_humans, born_producers, born_matter = evolve_humans(
        humans, producers, matter, world, epoch=100
    )
    after_human_mass = sum(human_element_totals(born_humans).values())
    after_plant_mass = sum(
        _plant_mass(cell) + sum(float(v) for v in cell["detritus_elements_kg"].values())
        + sum(float(v) for v in cell["seed_elements_kg"].values())
        for cell in born_producers["cells"]
    )

    # Death and decomposition: isolate one adult and force old-age death.
    dying = deepcopy(sim.human_state())
    dying["humans"] = [deepcopy(dying["humans"][0])]
    dying["humans"][0]["age_ticks"] = HUMAN_MAX_AGE_TICKS - 1
    dying["humans"][0]["energy"] = 20.0
    death_producers = deepcopy(sim.ecology_state())
    death_matter = deepcopy(sim.matter_state())
    death_world = deepcopy(sim.world_state())

    after_death, death_producers, death_matter = evolve_humans(
        dying, death_producers, death_matter, death_world, epoch=200
    )
    remains_after_death = sum(
        sum(float(v) for v in cell["elements_kg"].values()) + float(cell["water_kg"])
        for cell in after_death["remains_cells"]
    )
    matter_before_more_decay = sum(
        sum(float(v) for v in cell["elements_kg"].values()) + float(cell["soil_water_kg"])
        for cell in death_matter["cells"]
    )
    after_decay, _, matter_after_decay = evolve_humans(
        after_death, death_producers, death_matter, death_world, epoch=201
    )
    remains_after_decay = sum(
        sum(float(v) for v in cell["elements_kg"].values()) + float(cell["water_kg"])
        for cell in after_decay["remains_cells"]
    )
    matter_after_more_decay = sum(
        sum(float(v) for v in cell["elements_kg"].values()) + float(cell["soil_water_kg"])
        for cell in matter_after_decay["cells"]
    )

    # Physiology: deterministic heat stress followed by comfortable recovery.
    probe = deepcopy(sim.human_state()["humans"][0])
    probe["energy"] = 20.0
    probe["body_water_kg"] = 0.7
    probe["fatigue"] = 0.0
    probe["injury"] = 0.0
    _apply_physiology(probe, {"temperature": 60.0}, moved=True)
    stressed_fatigue = float(probe["fatigue"])
    stressed_injury = float(probe["injury"])
    stressed_core = float(probe["core_temperature_c"])
    _apply_physiology(probe, {"temperature": 22.0}, moved=False)

    return {
        "reproduction_occurred": int(born_humans.get("cumulative_births", 0)) >= 1,
        "birth_added_human": len(born_humans["humans"]) > len(humans["humans"]),
        "birth_material_accounted": abs(
            (after_human_mass + after_plant_mass)
            - (before_human_mass + before_plant_mass)
        ) < 5e-5,
        "old_age_death_occurred": int(after_death.get("cumulative_deaths", 0)) >= 1,
        "remains_created": remains_after_death > 0.0,
        "decomposition_reduces_remains": remains_after_decay < remains_after_death,
        "decomposition_returns_to_matter": matter_after_more_decay > matter_before_more_decay,
        "fatigue_changes_with_movement": stressed_fatigue > 0.0,
        "thermal_state_responds": stressed_core > 37.0,
        "thermal_exposure_can_injure": stressed_injury > 0.0,
        "injury_can_heal": float(probe["injury"]) < stressed_injury,
        "rest_reduces_fatigue": float(probe["fatigue"]) < stressed_fatigue,
    }


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

    focused = focused_biology_checks(direct)

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
            **focused,
            "physiology_state_present": all(
                all(key in h for key in ("fatigue", "injury", "core_temperature_c"))
                for h in final_humans["humans"]
            ),
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
