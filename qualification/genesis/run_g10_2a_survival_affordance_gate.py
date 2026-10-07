from __future__ import annotations

from copy import deepcopy

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.biology import _apply_physiology, _experienced_reward
from hrm_genesis.human.learning import update_expectations
from hrm_genesis.human.planning import choose_destination


def main() -> int:
    world = GenesisSimulation(
        GenesisConfig(
            master_seed="g10-2a-terrain",
            world_width=16,
            world_height=16,
        )
    ).world_state()
    covered = [cell for cell in world["cells"] if float(cell["terrain_cover"]) > 0.0]

    profile = {
        "calibrated": True,
        "water_capacity_kg": 42.0,
        "basal_energy_kcal_per_tick": 2000.0,
    }
    baseline = {
        "energy": 8000.0,
        "body_water_kg": 42.0,
        "fatigue": 0.0,
        "injury": 0.0,
        "core_temperature_c": 37.0,
    }
    exposed = deepcopy(baseline)
    protected = deepcopy(baseline)

    _apply_physiology(
        exposed,
        {"temperature": 60.0, "terrain_cover": 0.0},
        moved=False,
        profile=profile,
    )
    _apply_physiology(
        protected,
        {"temperature": 60.0, "terrain_cover": 0.8},
        moved=False,
        profile=profile,
        producer_cell={"woody_elements_kg": {"C": 8.0}},
    )

    exposed_reward = _experienced_reward(
        start_energy=8000.0,
        start_water=42.0,
        start_injury=0.0,
        human=exposed,
        profile=profile,
    )
    protected_reward = _experienced_reward(
        start_energy=8000.0,
        start_water=42.0,
        start_injury=0.0,
        human=protected,
        profile=profile,
    )

    expectations = {}
    expectations = update_expectations(
        expectations,
        {"origin": [0, 0], "cells": []},
        exposed_reward,
    )
    expectations = update_expectations(
        expectations,
        {"origin": [1, 0], "cells": []},
        protected_reward,
    )
    choice = choose_destination(
        {"x": 0, "y": 0},
        {
            "origin": [0, 0],
            "recognized": [],
            "cells": [
                {"x": 0, "y": 0, "food_kg": 1.0, "water_kg": 1.0},
                {"x": 1, "y": 0, "food_kg": 1.0, "water_kg": 1.0},
            ],
        },
        {"expectations": expectations, "uncertainty": 0.05},
    )

    checks = {
        "terrain_cover_exists": bool(covered),
        "terrain_cover_is_rare": bool(covered) and len(covered) / len(world["cells"]) < 0.15,
        "terrain_cover_requires_relief": all(
            float(cell["terrain_relief"]) >= 30.0 for cell in covered
        ),
        "terrain_cover_requires_rock": all(
            float(cell["rock_exposure"]) >= 0.88 for cell in covered
        ),
        "physical_cover_reduces_energy_cost": float(protected["energy"]) > float(exposed["energy"]),
        "physical_cover_reduces_injury": float(protected["injury"]) <= float(exposed["injury"]),
        "experienced_protection_has_better_reward": protected_reward > exposed_reward,
        "experience_changes_later_choice": choice == (1, 0),
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G10_2A_GATE_FAIL:", ", ".join(failed))
        return 1

    print(
        "G10_2A_RESULTS:",
        {
            "covered_cells": len(covered),
            "total_cells": len(world["cells"]),
            "exposed_reward": round(exposed_reward, 6),
            "protected_reward": round(protected_reward, 6),
            "learned_choice": choice,
        },
    )
    print("G10_2A_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
