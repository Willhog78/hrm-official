from __future__ import annotations

from .learning import expectation_for


def choose_destination(
    human: dict,
    perception: dict,
    cognition: dict,
) -> tuple[int, int]:
    """One-step bounded plan using only current perception and learned expectation."""
    ox, oy = map(int, perception["origin"])
    expectations = cognition.get("expectations", {})
    uncertainty = float(cognition.get("uncertainty", 1.0))

    def score(cell: dict) -> tuple[float, int, int]:
        x, y = int(cell["x"]), int(cell["y"])
        food = float(cell["food_kg"])
        water = float(cell["water_kg"])
        learned = expectation_for(expectations, x, y)
        distance = abs(x - ox) + abs(y - oy)
        # Direct evidence dominates; history biases ambiguous choices.
        value = food + 0.002 * water + learned * (1.0 - min(0.95, uncertainty))
        value -= 0.01 * distance
        return (round(value, 12), -y, -x)

    best = max(perception["cells"], key=score)
    return int(best["x"]), int(best["y"])
