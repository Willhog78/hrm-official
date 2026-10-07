from __future__ import annotations


def population_metrics(human_state: dict) -> dict:
    by_origin: dict[str, int] = {}
    occupied: dict[tuple[int, int], list[str]] = {}
    taught = 0
    learned_sequences = 0

    for human in human_state["humans"]:
        origin = str(human.get("population_id", "unassigned"))
        by_origin[origin] = by_origin.get(origin, 0) + 1
        xy = (int(human["x"]), int(human["y"]))
        occupied.setdefault(xy, []).append(str(human["id"]))
        if human.get("last_teacher_id"):
            taught += 1
        learned_sequences += len(human.get("learned_sequences", []))

    cross_origin_cells = 0
    for xy, ids in occupied.items():
        origins = {
            str(h.get("population_id", "unassigned"))
            for h in human_state["humans"]
            if str(h["id"]) in ids
        }
        if len(origins) > 1:
            cross_origin_cells += 1

    return {
        "human_count": len(human_state["humans"]),
        "by_population_origin": dict(sorted(by_origin.items())),
        "occupied_cells": len(occupied),
        "cross_origin_shared_cells": cross_origin_cells,
        "agents_with_teacher": taught,
        "learned_sequence_count": learned_sequences,
    }
