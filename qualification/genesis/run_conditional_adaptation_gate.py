from __future__ import annotations

from hrm_genesis.human.learning import update_expectations
from hrm_genesis.human.planning import choose_destination


def main() -> int:
    expectations = {}
    expectations = update_expectations(
        expectations,
        {"origin": [1, 0], "cells": [], "context": "hot"},
        100.0,
    )
    expectations = update_expectations(
        expectations,
        {"origin": [0, 0], "cells": [], "context": "mild"},
        20.0,
    )

    cognition = {"expectations": expectations, "uncertainty": 0.05}
    hot = {
        "origin": [0, 0],
        "context": "hot",
        "recognized": [],
        "cells": [
            {"x": 0, "y": 0, "food_kg": 1.2, "water_kg": 1.0},
            {"x": 1, "y": 0, "food_kg": 1.0, "water_kg": 1.0},
        ],
    }
    mild = {
        "origin": [0, 0],
        "context": "mild",
        "recognized": [],
        "cells": [
            {"x": 0, "y": 0, "food_kg": 1.2, "water_kg": 1.0},
            {"x": 1, "y": 0, "food_kg": 1.0, "water_kg": 1.0},
        ],
    }

    hot_choice = choose_destination({"x": 0, "y": 0}, hot, cognition)
    mild_choice = choose_destination({"x": 0, "y": 0}, mild, cognition)

    checks = {
        "harsh_context_reuses_protective_experience": hot_choice == (1, 0),
        "mild_context_does_not_force_cover": mild_choice == (0, 0),
    }
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if not all(checks.values()):
        print("CONDITIONAL_ADAPTATION_FAIL")
        return 1

    print("CONDITIONAL_ADAPTATION_RESULTS:", {"hot_choice": hot_choice, "mild_choice": mild_choice})
    print("CONDITIONAL_ADAPTATION_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
