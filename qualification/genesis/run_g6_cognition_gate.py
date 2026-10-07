from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.memory import FORGET_AFTER_TICKS, MAX_EPISODES, empty_memory, remember
from hrm_genesis.human.planning import choose_destination


def main() -> int:
    identical_perception = {
        "origin": [1, 1],
        "recognized": [],
        "cells": [
            {"x": 0, "y": 1, "food_kg": 1.0, "water_kg": 1.0},
            {"x": 2, "y": 1, "food_kg": 1.0, "water_kg": 1.0},
            {"x": 1, "y": 1, "food_kg": 0.2, "water_kg": 1.0},
        ],
    }
    agent = {"x": 1, "y": 1}
    history_left = {
        "expectations": {"0,1": 4.0, "2,1": -1.0},
        "uncertainty": 0.1,
    }
    history_right = {
        "expectations": {"0,1": -1.0, "2,1": 4.0},
        "uncertainty": 0.1,
    }
    left_choice = choose_destination(agent, identical_perception, history_left)
    right_choice = choose_destination(agent, identical_perception, history_right)


    hungry_perception = {
        "origin": [1, 1],
        "recognized": [],
        "forage_need_kg": 1.0,
        "energy_reserve_fraction": 0.20,
        "cells": [
            {"x": 1, "y": 1, "food_kg": 0.08, "water_kg": 1.0},
            {"x": 0, "y": 1, "food_kg": 0.0, "water_kg": 1.0},
            {"x": 2, "y": 1, "food_kg": 0.0, "water_kg": 1.0},
            {"x": 1, "y": 0, "food_kg": 0.0, "water_kg": 1.0},
            {"x": 1, "y": 2, "food_kg": 0.0, "water_kg": 1.0},
        ],
    }
    hungry_history = {
        "expectations": {},
        "contextual_expectations": {},
        "uncertainty": 0.2,
        "memory": {
            "episodes": [
                {"epoch": 1, "origin": [0, 1], "reward": -1.0},
                {"epoch": 2, "origin": [1, 0], "reward": -1.0},
                {"epoch": 3, "origin": [1, 2], "reward": -1.0},
            ],
            "locations": {},
            "recognized": [],
        },
    }
    hungry_choice = choose_destination(agent, hungry_perception, hungry_history)

    memory = empty_memory()
    for epoch in range(MAX_EPISODES + 12):
        perception = {
            "origin": [epoch % 2, 0],
            "recognized": ["human-peer"] if epoch == MAX_EPISODES + 11 else [],
            "cells": [{"x": epoch % 2, "y": 0, "food_kg": 0.1, "water_kg": 1.0}],
        }
        memory = remember(memory, perception, epoch, float(epoch))

    config = GenesisConfig(
        master_seed="genesis-g6-cognition",
        world_width=4,
        world_height=4,
        ticks_per_year=12,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_cognition_enabled=True,
    )
    direct = GenesisSimulation(config)
    direct.run(24)

    with TemporaryDirectory() as td:
        checkpoint = Path(td) / "g6-checkpoint.json"
        resumed = GenesisSimulation(config)
        resumed.run(12)
        resumed.write_checkpoint(checkpoint)
        resumed = GenesisSimulation.load_checkpoint(checkpoint, config)
        resumed.run(12)

        final_humans = direct.human_state()["humans"]
        cognition_states = [h.get("cognition") for h in final_humans]
        checks = {
            "different_history_different_choice": left_choice != right_choice,
            "hunger_drives_exploration_through_poor_neighbor": hungry_choice == (2, 1),
            "left_history_selects_left": left_choice == (0, 1),
            "right_history_selects_right": right_choice == (2, 1),
            "episodic_memory_bounded": len(memory["episodes"]) <= MAX_EPISODES,
            "forgetting_window_enforced": all(
                (MAX_EPISODES + 11) - int(e["epoch"]) <= FORGET_AFTER_TICKS
                for e in memory["episodes"]
            ),
            "individual_recognition_retained": "human-peer" in memory["recognized"],
            "cognition_integrated": bool(cognition_states) and all(c is not None for c in cognition_states),
            "memory_updates_in_world": bool(cognition_states) and all(len(c["memory"]["episodes"]) > 0 for c in cognition_states),
            "uncertainty_changes": bool(cognition_states) and all(float(c["uncertainty"]) < 1.0 for c in cognition_states),
            "checkpoint_replay": direct.human_state() == resumed.human_state(),
            "ledger_valid": direct.ledger.verify_chain() and resumed.ledger.verify_chain(),
            "no_language_or_technology": all(
                not any(key in h for key in ("language", "technology", "profession", "culture"))
                for h in final_humans
            ),
        }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G6_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G6_HISTORY_CHOICES:", {"left_history": left_choice, "right_history": right_choice, "hungry_exploration": hungry_choice})
    print("G6_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
