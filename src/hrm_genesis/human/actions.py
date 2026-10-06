from __future__ import annotations

PRIMITIVE_ACTIONS = (
    "move", "inspect", "grasp", "release", "carry", "consume",
    "transfer", "combine", "separate", "apply_force", "arrange", "signal",
)

def validate_sequence(sequence: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seq = tuple(str(x) for x in sequence)
    if not seq:
        raise ValueError("action sequence must not be empty")
    unknown = [x for x in seq if x not in PRIMITIVE_ACTIONS]
    if unknown:
        raise ValueError(f"unknown primitive actions: {unknown}")
    return seq

def execute_abstract_sequence(sequence: list[str] | tuple[str, ...], state: dict) -> tuple[dict, float]:
    """Execute a tiny qualification environment using only general primitives.

    The environment contains an inaccessible reward item and a movable object.
    No named technique exists in code. A useful sequence is simply one that
    changes the primitive state so the reward becomes accessible.
    """
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
