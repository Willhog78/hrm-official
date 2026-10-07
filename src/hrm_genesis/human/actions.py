from __future__ import annotations

from copy import deepcopy
from itertools import product


PRIMITIVE_ACTIONS = (
    "move", "inspect", "grasp", "release", "carry", "consume",
    "transfer", "combine", "separate", "apply_force", "arrange", "signal",
)

MANIPULATION_MASS_KG = 0.5


def validate_sequence(sequence: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seq = tuple(str(x) for x in sequence)
    if not seq:
        raise ValueError("action sequence must not be empty")
    unknown = [x for x in seq if x not in PRIMITIVE_ACTIONS]
    if unknown:
        raise ValueError(f"unknown primitive actions: {unknown}")
    return seq


def _mass(elements: dict[str, float]) -> float:
    return sum(float(v) for v in elements.values())


def _blank_like(elements: dict[str, float]) -> dict[str, float]:
    return {symbol: 0.0 for symbol in elements}


def _move_fraction(source: dict[str, float], fraction: float) -> dict[str, float]:
    moved = {}
    for symbol, raw in source.items():
        amount = max(0.0, float(raw) * fraction)
        source[symbol] = float(raw) - amount
        moved[symbol] = amount
    return moved


def _add_elements(target: dict[str, float], addition: dict[str, float]) -> None:
    for symbol, amount in addition.items():
        target[symbol] = float(target.get(symbol, 0.0)) + float(amount)


def execute_live_sequence(
    sequence: list[str] | tuple[str, ...],
    human: dict,
    producer_cell: dict,
) -> tuple[dict, dict, dict]:
    """Apply general primitives to real local material state.

    There is no named tool or shelter state. The action layer only transfers
    existing woody material through grasp/carry/release/arrange operations.
    """
    seq = validate_sequence(sequence)
    h = deepcopy(human)
    cell = deepcopy(producer_cell)

    wood = cell.setdefault("woody_elements_kg", {})
    loose = cell.setdefault("loose_material_elements_kg", _blank_like(wood))
    arranged = cell.setdefault("arranged_material_elements_kg", _blank_like(wood))
    geometry = cell.setdefault(
        "arrangement_geometry",
        {"span_m": 0.0, "height_m": 0.0, "density": 0.0, "surface_area_m2": 0.0},
    )
    held = h.setdefault("held_material_elements_kg", _blank_like(wood))

    trace = {
        "inspected": False,
        "carried": False,
        "released": False,
        "arranged": False,
        "material_moved_kg": 0.0,
        "effort_energy_kcal": 0.0,
    }

    for action in seq:
        if action == "inspect":
            trace["inspected"] = True
            trace["effort_energy_kcal"] += 1.0

        elif action == "grasp" and _mass(held) <= 1e-12:
            available = _mass(wood)
            if available > 0.0:
                fraction = min(1.0, MANIPULATION_MASS_KG / available)
                moved = _move_fraction(wood, fraction)
                _add_elements(held, moved)
                trace["material_moved_kg"] += _mass(moved)
                trace["effort_energy_kcal"] += 6.0 + 8.0 * _mass(moved)

        elif action == "carry" and _mass(held) > 0.0:
            trace["carried"] = True
            trace["effort_energy_kcal"] += 4.0 + 6.0 * _mass(held)

        elif action == "release" and _mass(held) > 0.0:
            moved = dict(held)
            for symbol in held:
                held[symbol] = 0.0
            _add_elements(loose, moved)
            trace["released"] = True
            trace["effort_energy_kcal"] += 2.0

        elif action == "arrange" and _mass(loose) > 0.0:
            moved = dict(loose)
            for symbol in loose:
                loose[symbol] = 0.0
            _add_elements(arranged, moved)
            moved_mass = _mass(moved)
            total_mass = _mass(arranged)
            geometry["span_m"] = min(2.5, float(geometry["span_m"]) + 0.45 + moved_mass * 0.35)
            geometry["height_m"] = min(2.2, float(geometry["height_m"]) + 0.20 + moved_mass * 0.30)
            geometry["surface_area_m2"] = min(
                8.0, float(geometry["surface_area_m2"]) + 0.5 + moved_mass * 0.9
            )
            geometry["density"] = min(1.0, total_mass / max(0.5, float(geometry["surface_area_m2"])))
            trace["arranged"] = True
            trace["effort_energy_kcal"] += 8.0 + 5.0 * moved_mass

        elif action == "separate" and _mass(arranged) > 0.0:
            fraction = min(1.0, MANIPULATION_MASS_KG / _mass(arranged))
            moved = _move_fraction(arranged, fraction)
            _add_elements(loose, moved)
            trace["effort_energy_kcal"] += 5.0 + 5.0 * _mass(moved)

        elif action == "combine" and _mass(loose) > 0.0:
            moved = dict(loose)
            for symbol in loose:
                loose[symbol] = 0.0
            _add_elements(arranged, moved)
            trace["arranged"] = True
            trace["effort_energy_kcal"] += 7.0 + 5.0 * _mass(moved)

        elif action == "apply_force" and _mass(wood) > 0.0:
            available = _mass(wood)
            fraction = min(1.0, (MANIPULATION_MASS_KG * 0.5) / available)
            moved = _move_fraction(wood, fraction)
            _add_elements(loose, moved)
            trace["material_moved_kg"] += _mass(moved)
            trace["effort_energy_kcal"] += 10.0 + 10.0 * _mass(moved)

    h["held_material_elements_kg"] = held
    cell["woody_elements_kg"] = wood
    cell["loose_material_elements_kg"] = loose
    cell["arranged_material_elements_kg"] = arranged
    cell["arrangement_geometry"] = geometry
    return h, cell, trace


def candidate_sequences(max_length: int = 5) -> tuple[tuple[str, ...], ...]:
    """Bounded primitive search space for discovery tests; no named outcome."""
    verbs = ("inspect", "grasp", "carry", "release", "arrange", "apply_force", "combine")
    sequences = []
    for length in range(1, max_length + 1):
        sequences.extend(product(verbs, repeat=length))
    return tuple(sequences)


def execute_abstract_sequence(sequence: list[str] | tuple[str, ...], state: dict) -> tuple[dict, float]:
    """Legacy qualification environment retained for regression coverage."""
    seq = validate_sequence(sequence)
    s = dict(state)
    holding = bool(s.get("holding", False))
    obstacle = bool(s.get("obstacle_present", True))
    reward_accessible = bool(s.get("reward_accessible", False))

    for action in seq:
        if action == "inspect":
            s["inspected"] = True
        elif action == "grasp" and obstacle:
            holding = True
        elif action == "carry" and holding:
            s["carried"] = True
        elif action == "release" and holding:
            holding = False
            if s.get("carried"):
                obstacle = False
        elif action == "apply_force" and obstacle:
            obstacle = False
        elif action == "arrange" and not obstacle:
            reward_accessible = True
        elif action == "consume" and reward_accessible:
            s["consumed_reward"] = True

    s["holding"] = holding
    s["obstacle_present"] = obstacle
    s["reward_accessible"] = reward_accessible
    reward = 1.0 if s.get("consumed_reward") else 0.0
    return s, reward
