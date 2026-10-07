from __future__ import annotations

from copy import deepcopy

from hrm_genesis.human.actions import (
    candidate_sequences,
    execute_live_sequence,
    validate_sequence,
)
from hrm_genesis.human.biology import _apply_physiology
from hrm_genesis.human.communication import imitate_signal, signal_sequence


ELEMENTS = {"C": 0.86, "N": 0.08, "K": 0.025, "P": 0.012, "Mg": 0.013, "S": 0.01}


def _scaled_elements(total_kg: float) -> dict[str, float]:
    return {symbol: total_kg * fraction for symbol, fraction in ELEMENTS.items()}


def _cell() -> dict:
    return {
        "x": 0,
        "y": 0,
        "plant_elements_kg": _scaled_elements(0.0),
        "woody_elements_kg": _scaled_elements(1.0),
        "loose_material_elements_kg": _scaled_elements(0.0),
        "arranged_material_elements_kg": _scaled_elements(0.0),
        "seed_elements_kg": _scaled_elements(0.0),
        "detritus_elements_kg": _scaled_elements(0.0),
        "age_ticks": 40,
    }


def _human(identity: str) -> dict:
    return {
        "id": identity,
        "energy": 8000.0,
        "body_water_kg": 42.0,
        "fatigue": 0.0,
        "injury": 0.0,
        "core_temperature_c": 37.0,
        "held_material_elements_kg": _scaled_elements(0.0),
        "learned_sequences": [],
        "last_teacher_id": None,
    }


PROFILE = {
    "calibrated": True,
    "water_capacity_kg": 42.0,
}


def _body_outcome(sequence: tuple[str, ...]) -> tuple[float, dict, dict, dict]:
    human, cell, trace = execute_live_sequence(sequence, _human("candidate"), _cell())
    human["energy"] = float(human["energy"]) - float(trace.get("effort_energy_kcal", 0.0))
    for _ in range(7):
        _apply_physiology(
            human,
            {"temperature": 60.0, "terrain_cover": 0.0},
            moved=False,
            profile=PROFILE,
            producer_cell=cell,
        )
    score = float(human["energy"]) - float(human["injury"]) * 4000.0
    return score, human, cell, trace


def _material_total(human: dict, cell: dict) -> float:
    buckets = [
        cell["woody_elements_kg"],
        cell["loose_material_elements_kg"],
        cell["arranged_material_elements_kg"],
        human.get("held_material_elements_kg", {}),
    ]
    return sum(float(v) for bucket in buckets for v in bucket.values())


def main() -> int:
    baseline_score, _, baseline_cell, _ = _body_outcome(("inspect",))

    best = None
    for candidate in candidate_sequences(max_length=4):
        score, human, cell, trace = _body_outcome(candidate)
        arranged_mass = sum(cell["arranged_material_elements_kg"].values())
        geometry = cell.get("arrangement_geometry", {})
        physically_changed = (
            trace["material_moved_kg"] > 0.0
            and arranged_mass > 0.0
            and float(geometry.get("surface_area_m2", 0.0)) > 0.0
        )
        if physically_changed and (best is None or score > best[0]):
            best = (score, candidate, human, cell, trace)

    assert best is not None
    teacher_score, discovered, teacher_body, teacher_cell, teacher_trace = best
    sequence = validate_sequence(discovered)

    teacher = _human("human-teacher")
    if teacher_score > baseline_score:
        teacher["learned_sequences"] = [list(sequence)]

    signal = signal_sequence(teacher, sequence)
    learner = imitate_signal(_human("human-learner"), signal)
    imitated = tuple(learner["learned_sequences"][-1])

    learner_after, learner_cell, learner_trace = execute_live_sequence(
        imitated,
        learner,
        _cell(),
    )
    learner_after["energy"] = float(learner_after["energy"]) - float(
        learner_trace.get("effort_energy_kcal", 0.0)
    )
    for _ in range(7):
        _apply_physiology(
            learner_after,
            {"temperature": 60.0, "terrain_cover": 0.0},
            moved=False,
            profile=PROFILE,
            producer_cell=learner_cell,
        )
    learner_score = float(learner_after["energy"]) - float(learner_after["injury"]) * 4000.0

    initial_material = sum(_scaled_elements(1.0).values())
    forbidden_named_tech = {
        "spear", "farm", "farming", "shelter", "tool", "technology",
        "profession", "civilization", "cooking",
    }
    causal_tokens = set(sequence) | {
        str(k).lower() for k in teacher.keys()
    } | {
        str(k).lower() for k in learner.keys()
    }

    checks = {
        "teacher_discovers_useful_live_behavior": teacher_score > baseline_score,
        "behavior_changes_real_material_state": teacher_trace["material_moved_kg"] > 0.0,
        "behavior_creates_arranged_material": sum(teacher_cell["arranged_material_elements_kg"].values()) > 0.0,
        "live_material_is_conserved": abs(_material_total(teacher_body, teacher_cell) - initial_material) < 1e-9,
        "signal_contains_sequence": tuple(signal["primitive_sequence"]) == sequence,
        "learner_retains_transmission": imitated == sequence,
        "teacher_identity_retained": learner["last_teacher_id"] == teacher["id"],
        "learner_reproduces_live_effect": learner_score > baseline_score,
        "learner_material_is_conserved": abs(_material_total(learner_after, learner_cell) - initial_material) < 1e-9,
        "no_named_technology_in_causal_state": not (causal_tokens & forbidden_named_tech),
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print(
        "G7_LIVE_RESULTS:",
        {
            "sequence": list(sequence),
            "baseline_score": round(baseline_score, 6),
            "teacher_score": round(teacher_score, 6),
            "learner_score": round(learner_score, 6),
            "arranged_material_kg": round(sum(teacher_cell["arranged_material_elements_kg"].values()), 6),
        },
    )

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G7_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G7_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
