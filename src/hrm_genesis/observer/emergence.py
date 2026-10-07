from __future__ import annotations


def classify_emergence(human_state: dict) -> dict:
    """Descriptive labels only. Return value is never causal state."""
    humans = list(human_state["humans"])

    by_cell: dict[tuple[int, int], list[dict]] = {}
    for human in humans:
        xy = (int(human["x"]), int(human["y"]))
        by_cell.setdefault(xy, []).append(human)

    persistent_groups = sum(1 for members in by_cell.values() if len(members) >= 2)

    transmitted = [
        h for h in humans
        if h.get("last_teacher_id") and h.get("learned_sequences")
    ]

    sequence_holders: dict[tuple[str, ...], set[str]] = {}
    for human in humans:
        for sequence in human.get("learned_sequences", []):
            key = tuple(str(x) for x in sequence)
            sequence_holders.setdefault(key, set()).add(str(h["id"]))

    shared_behaviors = sum(1 for holders in sequence_holders.values() if len(holders) >= 2)

    return {
        "persistent_groups_detected": persistent_groups,
        "behavior_transmission_detected": len(transmitted),
        "shared_technique_like_patterns": shared_behaviors,
        "exchange_detected": False,
        "specialization_detected": False,
        "conflict_detected": False,
        "hierarchy_detected": False,
        "notes": "Labels are observer descriptions and do not write into causal state.",
    }
