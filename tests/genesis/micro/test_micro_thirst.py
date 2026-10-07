"""MICRO: thirst. Does the thirst drive pick behaviour consistent with
physiological urgency, using only perceived or remembered water?"""

from __future__ import annotations

from _scenario import Scenario

THIRSTY = 0.85  # fraction of water capacity: short of full, ~6 days above the lethal floor


def _thirsty(sc: Scenario, x: int, y: int, **fields):
    cap = float(sc.profile["water_capacity_kg"])
    return sc.set_agent(x, y, body_water_kg=cap * THIRSTY, **fields)


def test_water_in_current_cell_is_drunk_and_hydration_rises():
    sc = Scenario()
    _thirsty(sc, 2, 0)
    sc.set_water(2, 0, 5000.0)
    sc.set_pool(2, 0, "plant_elements_kg", 500.0)
    before_cell = sc.water(2, 0)
    sc.step()
    cap = float(sc.profile["water_capacity_kg"])
    assert sc.xy == (2, 0), f"moved away from water it was standing in: {sc.xy}"
    # Drinks to capacity, then loses one day's turnover.
    assert abs(sc.agent["body_water_kg"] - (cap - float(sc.profile["water_loss_per_tick_kg"]))) < 1e-6
    assert before_cell - sc.water(2, 0) > 0.0, "drinking must debit the cell's water"


def test_water_one_cell_away_is_reached_and_drunk_next_step():
    sc = Scenario()
    _thirsty(sc, 2, 0)
    sc.set_pool(2, 0, "plant_elements_kg", 5000.0)  # food here, no water
    sc.set_water(3, 0, 5000.0)
    sc.set_pool(3, 0, "plant_elements_kg", 50.0)
    start = sc.agent["body_water_kg"]
    sc.step()
    assert sc.xy == (3, 0), f"thirsty agent ignored adjacent water; at {sc.xy}"
    assert sc.agent["body_water_kg"] > start


def test_remembered_water_several_cells_away_is_walked_to():
    sc = Scenario(width=7)
    _thirsty(sc, 0, 0)
    sc.set_pool(0, 0, "plant_elements_kg", 5000.0)
    sc.set_water(5, 0, 5000.0)
    sc.remember(5, 0, water_kg=5000.0)
    path = []
    for _ in range(6):
        sc.step()
        path.append(sc.xy)
        if sc.xy == (5, 0):
            break
    assert path[-1] == (5, 0), f"did not reach remembered water: path {path}"
    assert all(b[0] - a[0] == 1 for a, b in zip([(0, 0)] + path, path)), f"not a direct walk: {path}"


def test_unknown_distant_water_is_not_known():
    """No global knowledge: water two cells away that was never seen exerts no pull."""
    sc = Scenario(width=7)
    _thirsty(sc, 0, 0)
    sc.set_water(5, 0, 5000.0)
    sc.agent["cognition"]["memory"]["locations"] = {}
    sc.step()
    # It may explore, but it cannot step straight toward water it cannot know of
    # any more than the other way; on a 1-row world exploration goes to (1, 0).
    assert sc.xy in {(0, 0), (1, 0)}


def test_dehydration_more_urgent_than_food_takes_agent_to_water():
    sc = Scenario()
    cap = float(sc.profile["water_capacity_kg"])
    sc.set_agent(2, 0, body_water_kg=cap * 0.56, energy=float(sc.profile["energy_capacity_kcal"]) * 0.5)
    sc.set_pool(2, 0, "plant_elements_kg", 5000.0)
    sc.set_water(1, 0, 5000.0)  # no food there
    sc.step()
    assert sc.xy == (1, 0), f"stayed with food while near death from thirst: {sc.xy}"


def test_starvation_more_urgent_than_thirst_takes_agent_to_food():
    sc = Scenario()
    sc.set_agent(2, 0, body_water_kg=float(sc.profile["water_capacity_kg"]) * 0.9, energy=300.0)
    sc.set_pool(3, 0, "plant_elements_kg", 50.0)  # enough for a day, no water
    sc.set_water(1, 0, 5000.0)  # water, no food
    sc.step()
    assert sc.xy == (3, 0), f"went for water although starvation was closer: {sc.xy}"


def test_both_needs_met_in_one_cell_beats_either_alone():
    sc = Scenario()
    cap = float(sc.profile["water_capacity_kg"])
    sc.set_agent(2, 0, body_water_kg=cap * 0.6, energy=300.0)
    sc.set_pool(1, 0, "plant_elements_kg", 50.0)
    sc.set_pool(3, 0, "plant_elements_kg", 50.0)
    sc.set_water(3, 0, 5000.0)
    sc.step()
    assert sc.xy == (3, 0)


def test_no_repeated_useless_water_seeking_when_hydrated():
    sc = Scenario()
    sc.set_agent(2, 0)
    sc.set_water(2, 0, 50000.0)
    sc.set_pool(2, 0, "plant_elements_kg", 50000.0)
    sc.set_water(3, 0, 50000.0)
    positions = []
    for _ in range(10):
        sc.step()
        positions.append(sc.xy)
    moves = sum(1 for a, b in zip(positions, positions[1:]) if a != b)
    assert moves == 0, f"hydrated, fed agent kept moving: {positions}"
