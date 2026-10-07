from __future__ import annotations

from .learning import contextual_expectation_for, expectation_for


def _food(cell: dict) -> float:
    """The agent's own estimate of edible food in a cell.

    Capacity model v1 supplies `expected_food_kg` (learned values over all
    visible kinds); earlier models see plant tissue only.
    """
    return float(cell.get("expected_food_kg", cell["food_kg"]))


def _step_toward(origin: tuple[int, int], target: tuple[int, int], cells: list[dict]) -> tuple[int, int] | None:
    ox, oy = origin
    options = [(int(c["x"]), int(c["y"])) for c in cells if (int(c["x"]), int(c["y"])) != origin]
    if not options:
        return None
    return min(options, key=lambda xy: (abs(xy[0] - target[0]) + abs(xy[1] - target[1]), xy[1], xy[0]))


def _least_visited_neighbor(perception: dict, cognition: dict, prefer) -> tuple[int, int] | None:
    ox, oy = map(int, perception["origin"])
    visits: dict[tuple[int, int], int] = {}
    for episode in cognition.get("memory", {}).get("episodes", []):
        key = tuple(map(int, episode.get("origin", (ox, oy))))
        visits[key] = visits.get(key, 0) + 1
    candidates = [c for c in perception["cells"] if (int(c["x"]), int(c["y"])) != (ox, oy)]
    if not candidates:
        return None
    best = min(candidates, key=lambda c: (visits.get((int(c["x"]), int(c["y"])), 0), -prefer(c), int(c["y"]), int(c["x"])))
    return int(best["x"]), int(best["y"])


def _thirst_destination(
    perception: dict,
    cognition: dict,
    forage_need: float,
    reserve_fraction: float,
) -> tuple[int, int] | None:
    """Thirst as an interoceptive drive (enabled by `agentus_thirst_enabled`).

    The agent feels how many days its water and energy reserves would last
    (`hydration_days`, `energy_days`). When the cell it stands on cannot refill
    today's water need, it seeks visible water, then remembered water, then
    unexplored ground. If hunger is also pressing and would kill sooner, the
    hunger rules decide instead. Without the perception keys this is inert.
    """
    if "water_need_kg" not in perception:
        return None
    ox, oy = map(int, perception["origin"])
    need = float(perception["water_need_kg"])
    here = next(c for c in perception["cells"] if (int(c["x"]), int(c["y"])) == (ox, oy))
    if float(here["water_kg"]) >= need:
        return None
    wet = [c for c in perception["cells"] if float(c["water_kg"]) >= need]
    # A visible cell that offers both today's water and today's food satisfies
    # hunger and thirst at once; hunger has no reason to hold the agent back.
    wet_and_fed = [c for c in wet if _food(c) >= forage_need]
    if wet_and_fed:
        best = min(wet_and_fed, key=lambda c: (
            abs(int(c["x"]) - ox) + abs(int(c["y"]) - oy), -float(c["water_kg"]), int(c["y"]), int(c["x"]),
        ))
        return int(best["x"]), int(best["y"])

    # Otherwise going for water would cost the day's food. If starvation is
    # closer than dehydration, the hunger rules decide.
    hungry = forage_need > 0.0 and reserve_fraction < 0.75
    if hungry and float(perception.get("energy_days", 1e9)) < float(perception.get("hydration_days", 0.0)):
        return None

    if wet:
        best = min(wet, key=lambda c: (
            0 if _food(c) >= forage_need else 1,
            abs(int(c["x"]) - ox) + abs(int(c["y"]) - oy),
            -float(c["water_kg"]),
            int(c["y"]), int(c["x"]),
        ))
        return int(best["x"]), int(best["y"])

    recalled = [
        (abs(int(px) - ox) + abs(int(py) - oy), -int(seen), int(py), int(px))
        for px, py, water, seen in perception.get("remembered_water", [])
        if float(water) >= need
    ]
    if recalled:
        _, _, ty, tx = min(recalled)
        step = _step_toward((ox, oy), (tx, ty), perception["cells"])
        if step is not None:
            return step
    return _least_visited_neighbor(perception, cognition, lambda c: float(c["water_kg"]))


def choose_destination(
    human: dict,
    perception: dict,
    cognition: dict,
) -> tuple[int, int]:
    """One-step bounded plan using only current perception and learned expectation."""
    ox, oy = map(int, perception["origin"])
    expectations = cognition.get("expectations", {})
    uncertainty = float(cognition.get("uncertainty", 1.0))

    forage_need = max(0.0, float(perception.get("forage_need_kg", 0.0)))
    reserve_fraction = max(0.0, min(1.0, float(perception.get("energy_reserve_fraction", 1.0))))
    visible_max_food = max(_food(cell) for cell in perception["cells"])

    thirst_target = _thirst_destination(perception, cognition, forage_need, reserve_fraction)
    if thirst_target is not None:
        return thirst_target
    if forage_need > 0.0 and reserve_fraction < 0.75 and visible_max_food >= forage_need:
        # When reserves are low, satisfy a visible daily food requirement before
        # comparing surplus water or rewards learned under different conditions.
        viable = [cell for cell in perception["cells"] if _food(cell) >= forage_need]
        best = max(viable, key=lambda cell: (
            _food(cell),
            -abs(int(cell["x"]) - ox) - abs(int(cell["y"]) - oy),
            -int(cell["y"]), -int(cell["x"]),
        ))
        return int(best["x"]), int(best["y"])
    hungry_local_failure = (
        forage_need > 0.0
        and reserve_fraction < 0.75
        and visible_max_food < forage_need
    )

    if hungry_local_failure and perception.get("remembered_food"):
        # Return toward a remembered place that held enough food. Memory is the
        # agent's own and may be stale; the trip costs real movement energy.
        recalled = [
            (abs(int(px) - ox) + abs(int(py) - oy), -int(seen), int(py), int(px))
            for px, py, food, seen in perception["remembered_food"]
            if float(food) >= forage_need
        ]
        if recalled:
            _, _, ty, tx = min(recalled)
            step = _step_toward((ox, oy), (tx, ty), perception["cells"])
            if step is not None:
                return step

    if hungry_local_failure:
        episodes = cognition.get("memory", {}).get("episodes", [])
        recent_visits: dict[tuple[int, int], int] = {}
        for episode in episodes:
            ex, ey = map(int, episode.get("origin", (ox, oy)))
            key = (ex, ey)
            recent_visits[key] = recent_visits.get(key, 0) + 1

        candidates = [
            cell for cell in perception["cells"]
            if (int(cell["x"]), int(cell["y"])) != (ox, oy)
        ]
        if candidates:
            best = min(
                candidates,
                key=lambda cell: (
                    recent_visits.get((int(cell["x"]), int(cell["y"])), 0),
                    -_food(cell),
                    int(cell["y"]),
                    int(cell["x"]),
                ),
            )
            return int(best["x"]), int(best["y"])

    def score(cell: dict) -> tuple[float, int, int]:
        x, y = int(cell["x"]), int(cell["y"])
        food = _food(cell)
        water = float(cell["water_kg"])
        learned = expectation_for(expectations, x, y)
        contextual = contextual_expectation_for(
            cognition.get("contextual_expectations", {}),
            x,
            y,
            str(perception.get("context", "mild")),
        )
        distance = abs(x - ox) + abs(y - oy)
        # Direct evidence dominates; history biases ambiguous choices.
        value = food + 0.002 * water + (learned + contextual) * (1.0 - min(0.95, uncertainty))
        value -= 0.01 * distance
        return (round(value, 12), -y, -x)

    best = max(perception["cells"], key=score)
    return int(best["x"]), int(best["y"])
