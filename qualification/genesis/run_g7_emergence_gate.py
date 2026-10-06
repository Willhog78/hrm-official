from __future__ import annotations

from hrm_genesis.human.actions import execute_abstract_sequence, validate_sequence
from hrm_genesis.human.communication import imitate_signal, signal_sequence


def main() -> int:
    initial = {
        "holding": False,
        "obstacle_present": True,
        "reward_accessible": False,
    }

    # No named technique: just a candidate sequence of general primitives.
    discovered = ["inspect", "grasp", "carry", "release", "arrange", "consume"]
    sequence = validate_sequence(discovered)

    teacher_final, teacher_reward = execute_abstract_sequence(sequence, initial)

    teacher = {
        "id": "human-teacher",
        "learned_sequences": [list(sequence)] if teacher_reward > 0 else [],
        "last_teacher_id": None,
    }
    learner = {
        "id": "human-learner",
        "learned_sequences": [],
        "last_teacher_id": None,
    }

    signal = signal_sequence(teacher, sequence)
    learner = imitate_signal(learner, signal)
    imitated = tuple(learner["learned_sequences"][-1])
    learner_final, learner_reward = execute_abstract_sequence(imitated, initial)

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
        "teacher_discovers_useful_behavior": teacher_reward > 0.0,
        "behavior_is_primitive_sequence": all(step in {
            "move", "inspect", "grasp", "release", "carry", "consume",
            "transfer", "combine", "separate", "apply_force", "arrange", "signal",
        } for step in sequence),
        "signal_contains_sequence": tuple(signal["primitive_sequence"]) == sequence,
        "learner_retains_transmission": imitated == sequence,
        "teacher_identity_retained": learner["last_teacher_id"] == teacher["id"],
        "learner_succeeds_by_imitation": learner_reward > 0.0,
        "same_sequence_same_result": learner_final == teacher_final,
        "no_named_technology_in_causal_state": not (causal_tokens & forbidden_named_tech),
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G7_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G7_SEQUENCE:", list(sequence))
    print("G7_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
