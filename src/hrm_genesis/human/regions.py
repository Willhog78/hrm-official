from __future__ import annotations


POPULATION_IDS = ("population-0", "population-1", "population-2", "population-3")


def region_bounds(width: int, height: int) -> dict[str, tuple[int, int, int, int]]:
    if width < 4 or height < 4:
        raise ValueError("multi-population world requires width and height >= 4")
    mx = width // 2
    my = height // 2
    return {
        "population-0": (0, mx - 1, 0, my - 1),
        "population-1": (mx, width - 1, 0, my - 1),
        "population-2": (0, mx - 1, my, height - 1),
        "population-3": (mx, width - 1, my, height - 1),
    }


def region_for_xy(x: int, y: int, width: int, height: int) -> str:
    mx = width // 2
    my = height // 2
    if y < my:
        return "population-0" if x < mx else "population-1"
    return "population-2" if x < mx else "population-3"


def cells_for_population(population_id: str, width: int, height: int) -> tuple[tuple[int, int], ...]:
    bounds = region_bounds(width, height)
    if population_id not in bounds:
        raise ValueError(f"unknown population_id: {population_id}")
    x0, x1, y0, y1 = bounds[population_id]
    return tuple((x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1))


def population_anchor(population_id: str, width: int, height: int, member_index: int = 0) -> tuple[int, int]:
    cells = cells_for_population(population_id, width, height)
    return cells[min(max(0, member_index), len(cells) - 1)]


def resource_profile(population_id: str, producer_state: dict, matter_state: dict) -> dict[str, float]:
    width = int(producer_state["width"])
    height = int(producer_state["height"])
    pcells = {(int(c["x"]), int(c["y"])): c for c in producer_state["cells"]}
    mcells = {(int(c["x"]), int(c["y"])): c for c in matter_state["cells"]}
    cells = cells_for_population(population_id, width, height)

    food = [
        sum(float(v) for v in pcells[xy]["plant_elements_kg"].values())
        for xy in cells
    ]
    water = [
        float(mcells[xy]["surface_water_kg"]) + float(mcells[xy]["soil_water_kg"])
        for xy in cells
    ]
    return {
        "mean_food_kg": sum(food) / len(food),
        "mean_water_kg": sum(water) / len(water),
        "max_food_kg": max(food),
        "max_water_kg": max(water),
    }


def population_counts(human_state: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for human in human_state["humans"]:
        pid = str(human.get("population_id", "unassigned"))
        counts[pid] = counts.get(pid, 0) + 1
    return dict(sorted(counts.items()))
