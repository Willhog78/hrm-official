"""G10.4: thirst as a planning drive. Physiology is unchanged; only decisions
gain access to the body's water state."""

from __future__ import annotations

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human.biology import _add_interoception
from hrm_genesis.human.planning import choose_destination


def _perception(cells, **extra):
    base = {"origin": [1, 1], "forage_need_kg": 1.14, "energy_reserve_fraction": 0.93, "cells": cells}
    base.update(extra)
    return base


DRY_RICH_HERE = [
    {"x": 1, "y": 1, "food_kg": 900.0, "water_kg": 0.0},
    {"x": 0, "y": 1, "food_kg": 50.0, "water_kg": 34000.0},
    {"x": 2, "y": 1, "food_kg": 0.0, "water_kg": 0.0},
]


def test_without_thirst_signal_agent_stays_on_dry_food_rich_cell():
    # The defect this phase repairs: food dominates and water is ignored.
    assert choose_destination({}, _perception(DRY_RICH_HERE), {}) == (1, 1)


def test_thirsty_agent_moves_to_adjacent_water():
    perception = _perception(DRY_RICH_HERE, water_need_kg=5.0, hydration_days=4.0, energy_days=14.0)
    assert choose_destination({}, perception, {}) == (0, 1)


def test_agent_does_not_move_when_it_can_drink_here():
    cells = [dict(DRY_RICH_HERE[0], water_kg=100.0)] + DRY_RICH_HERE[1:]
    perception = _perception(cells, water_need_kg=5.0, hydration_days=4.0, energy_days=14.0)
    assert choose_destination({}, perception, {}) == (1, 1)


def test_thirsty_agent_heads_toward_remembered_water_when_none_visible():
    cells = [{"x": x, "y": y, "food_kg": 0.0, "water_kg": 0.0} for x, y in [(1, 1), (0, 1), (2, 1), (1, 0), (1, 2)]]
    perception = _perception(cells, water_need_kg=5.0, hydration_days=4.0, energy_days=14.0,
                             remembered_water=[[1, 4, 20000.0, 10]])
    assert choose_destination({}, perception, {}) == (1, 2)
    # Remembered places too dry to help are ignored; the agent explores instead.
    perception["remembered_water"] = [[1, 4, 1.0, 10]]
    assert choose_destination({}, perception, {}) != (1, 1)


def test_more_urgent_hunger_takes_priority_over_thirst():
    cells = [
        {"x": 1, "y": 1, "food_kg": 0.0, "water_kg": 0.0},
        {"x": 0, "y": 1, "food_kg": 0.0, "water_kg": 34000.0},
        {"x": 2, "y": 1, "food_kg": 5.0, "water_kg": 0.0},
    ]
    starving = _perception(cells, energy_reserve_fraction=0.02, water_need_kg=5.0, hydration_days=7.0, energy_days=0.3)
    assert choose_destination({}, starving, {}) == (2, 1)
    parched = _perception(cells, energy_reserve_fraction=0.5, water_need_kg=5.0, hydration_days=1.0, energy_days=7.0)
    assert choose_destination({}, parched, {}) == (0, 1)


def test_interoception_reports_days_of_reserve_and_recalls_only_unseen_places():
    profile = {"water_capacity_kg": 42.0, "water_loss_per_tick_kg": 2.5, "basal_energy_kcal_per_tick": 2000.0}
    human = {"body_water_kg": 31.0, "energy": 10000.0, "cognition": {"memory": {"locations": {
        "1,1": {"water_kg": 0.0, "last_seen_epoch": 3}, "5,5": {"water_kg": 900.0, "last_seen_epoch": 2}}}}}
    perception = {"origin": [1, 1], "cells": [{"x": 1, "y": 1}]}
    _add_interoception(perception, human, profile, {"min_water_fraction": 0.5})
    assert perception["water_need_kg"] == 11.0 + 2.5
    assert perception["hydration_days"] == (31.0 - 21.0) / 2.5
    assert perception["energy_days"] == 5.0
    assert perception["remembered_water"] == [[5, 5, 900.0, 2]]


def test_flag_is_versioned_and_inert_when_off():
    kwargs = dict(master_seed="t", world_width=8, world_height=8, producer_ecology_enabled=True,
                  consumer_ecology_enabled=True, human_biology_enabled=True, human_cognition_enabled=True)
    off = GenesisConfig(**kwargs)
    on = GenesisConfig(**kwargs, agentus_thirst_enabled=True)
    assert "agentus_thirst_enabled" not in off.canonical()
    assert on.fingerprint() != off.fingerprint()
    assert "thirst_planning" not in GenesisSimulation(off).human_state()
    assert GenesisSimulation(on).human_state()["thirst_planning"] is True
