from hrm_genesis.human.actions import execute_abstract_sequence
from hrm_genesis.human.communication import imitate_signal, signal_sequence


def test_useful_primitive_sequence_can_be_transmitted_and_imitated():
    sequence = ["inspect", "grasp", "carry", "release", "arrange", "consume"]
    start = {"holding": False, "obstacle_present": True, "reward_accessible": False}

    _, teacher_reward = execute_abstract_sequence(sequence, start)
    assert teacher_reward > 0

    teacher = {"id": "a", "learned_sequences": [sequence], "last_teacher_id": None}
    learner = {"id": "b", "learned_sequences": [], "last_teacher_id": None}

    learner = imitate_signal(learner, signal_sequence(teacher, sequence))
    _, learner_reward = execute_abstract_sequence(learner["learned_sequences"][-1], start)

    assert learner_reward > 0
    assert learner["last_teacher_id"] == "a"
