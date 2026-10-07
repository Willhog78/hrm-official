from __future__ import annotations


def perceive_local(
    human: dict,
    producer_state: dict,
    matter_state: dict,
    peers: list[dict] | None = None,
    world_state: dict | None = None,
) -> dict:
    """Return only the organism's current cell plus immediate orthogonal neighbors."""
    width, height = int(producer_state["width"]), int(producer_state["height"])
    pcells = {(int(c["x"]), int(c["y"])): c for c in producer_state["cells"]}
    mcells = {(int(c["x"]), int(c["y"])): c for c in matter_state["cells"]}
    wcells = (
        {(int(c["x"]), int(c["y"])): c for c in world_state["cells"]}
        if world_state is not None
        else {}
    )
    x, y = int(human["x"]), int(human["y"])
    coords = [(x, y)]
    if x > 0:
        coords.append((x - 1, y))
    if x + 1 < width:
        coords.append((x + 1, y))
    if y > 0:
        coords.append((x, y - 1))
    if y + 1 < height:
        coords.append((x, y + 1))

    observations = []
    for xy in sorted(coords):
        p = pcells[xy]
        m = mcells[xy]
        w = wcells.get(xy, {})
        observations.append(
            {
                "x": xy[0],
                "y": xy[1],
                "food_kg": round(sum(float(v) for v in p["plant_elements_kg"].values()), 10),
                "water_kg": round(float(m["surface_water_kg"]) + float(m["soil_water_kg"]), 10),
                "woody_kg": round(sum(float(v) for v in p.get("woody_elements_kg", {}).values()), 10),
                "rock_exposure": round(float(w.get("rock_exposure", 0.0)), 10),
                "terrain_cover": round(float(w.get("terrain_cover", 0.0)), 10),
            }
        )
    recognized = []
    for peer in peers or []:
        if peer.get("id") == human.get("id"):
            continue
        px, py = int(peer["x"]), int(peer["y"])
        if abs(px - x) + abs(py - y) <= 1:
            recognized.append(str(peer["id"]))
    return {"origin": [x, y], "cells": observations, "recognized": sorted(recognized)}
