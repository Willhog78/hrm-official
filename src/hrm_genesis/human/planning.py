from __future__ import annotations

from .learning import contextual_expectation_for, expectation_for


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
    visible_max_food = max(float(cell["food_kg"]) for cell in perception["cells"])
    if forage_need > 0.0 and reserve_fraction < 0.75 and visible_max_food >= forage_need:
        # When reserves are low, satisfy a visible daily food requirement before
        # comparing surplus water or rewards learned under different conditions.
        viable = [cell for cell in perception["cells"] if float(cell["food_kg"]) >= forage_need]
        best = max(viable, key=lambda cell: (
            float(cell["food_kg"]),
            -abs(int(cell["x"]) - ox) - abs(int(cell["y"]) - oy),
            -int(cell["y"]), -int(cell["x"]),
        ))
        return int(best["x"]), int(best["y"])
    hungry_local_failure = (
        forage_need > 0.0
        and reserve_fraction < 0.75
        and visible_max_food < forage_need
    )

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
                    -float(cell["food_kg"]),
                    int(cell["y"]),
                    int(cell["x"]),
                ),
            )
            return int(best["x"]), int(best["y"])

    def score(cell: dict) -> tuple[float, int, int]:
        x, y = int(cell["x"]), int(cell["y"])
        food = float(cell["food_kg"])
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
