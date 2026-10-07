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
                "temperature": round(float(w.get("temperature", 22.0)), 10),
            }
        )
    recognized = []
    for peer in peers or []:
        if peer.get("id") == human.get("id"):
            continue
        px, py = int(peer["x"]), int(peer["y"])
        if abs(px - x) + abs(py - y) <= 1:
            recognized.append(str(peer["id"]))
    origin_cell = next(cell for cell in observations if int(cell["x"]) == x and int(cell["y"]) == y)
    ambient = float(origin_cell.get("temperature", 22.0))
    if ambient >= 36.0:
        context = "hot"
    elif ambient <= 8.0:
        context = "cold"
    else:
        context = "mild"
    return {
        "origin": [x, y],
        "cells": observations,
        "recognized": sorted(recognized),
        "context": context,
    }


def extend_perception_with_materials(
    perception: dict,
    producer_state: dict,
    consumer_state: dict,
    lithic_cells: dict,
    objects: list[dict],
    food_values: dict[str, float],
    food_reference: float,
    access_kg: dict[str, float],
    remembered: dict | None = None,
) -> dict:
    """Capacity model v1: add locally visible material, animals and the agent's
    *own* expectation of food in each visible cell.

    `expected_food_kg` is plant-tissue-equivalent mass: what is visible, limited
    by what can be gathered in a day, weighted by the agent's learned value of
    each kind relative to its innate plant-tissue reference. Unknown kinds count
    for nothing. No hidden nutritional label is exposed.
    """
    pcells = {(int(c["x"]), int(c["y"])): c for c in producer_state["cells"]}
    ccells = {(int(c["x"]), int(c["y"])): c for c in consumer_state["carcass_cells"]}
    animals_at: dict[tuple[int, int], list[str]] = {}
    for animal in consumer_state.get("animals", []):
        animals_at.setdefault((int(animal["x"]), int(animal["y"])), []).append(str(animal["species"]))
    objects_at: dict[tuple[int, int], int] = {}
    for obj in objects:
        if obj.get("holder") is None:
            xy = (int(obj["x"]), int(obj["y"]))
            objects_at[xy] = objects_at.get(xy, 0) + 1

    def mass(elements: dict) -> float:
        return sum(float(v) for v in elements.values())

    reference = max(1e-9, float(food_reference))
    for cell in perception["cells"]:
        xy = (int(cell["x"]), int(cell["y"]))
        p, c = pcells[xy], ccells[xy]
        visible = {
            "plant_tissue": mass(p["plant_elements_kg"]),
            "seed": mass(p["seed_elements_kg"]),
            "fresh_tissue": mass(c.get("fresh_elements_kg", {})),
            "decayed_tissue": mass(c["elements_kg"]),
            "woody_tissue": mass(p.get("woody_elements_kg", {})),
        }
        cell["seed_kg"] = round(visible["seed"], 10)
        cell["fresh_tissue_kg"] = round(visible["fresh_tissue"], 10)
        cell["decayed_tissue_kg"] = round(visible["decayed_tissue"], 10)
        cell["animals"] = sorted(animals_at.get(xy, []))
        cell["loose_stones"] = len(lithic_cells.get(f"{xy[0]},{xy[1]}", [])) + objects_at.get(xy, 0)
        expected = 0.0
        for kind, kg in visible.items():
            value = float(food_values.get(kind, 0.0))
            if value <= 0.0 or kg <= 0.0:
                continue
            expected += min(kg, float(access_kg.get(kind, kg))) * value / reference
        cell["expected_food_kg"] = round(expected, 10)

    if remembered is not None:
        x, y = map(int, perception["origin"])
        visible_xy = {(int(c["x"]), int(c["y"])) for c in perception["cells"]}
        recalled = []
        for key, place in sorted(remembered.items()):
            px, py = map(int, key.split(","))
            if (px, py) in visible_xy:
                continue
            food = float(place.get("expected_food_kg", place.get("food_kg", 0.0)))
            recalled.append([px, py, round(food, 10), int(place.get("last_seen_epoch", 0))])
        perception["remembered_food"] = recalled
    return perception
