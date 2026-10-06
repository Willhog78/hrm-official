from __future__ import annotations

from .grid import by_coordinate, neighbors


def diffuse_nutrients(cells: list[dict], width: int, height: int, rate: float = 0.01) -> None:
    if not 0.0 <= rate <= 0.25:
        raise ValueError("nutrient diffusion rate outside safe range")

    lookup = by_coordinate(cells)
    delta = {(int(c["x"]), int(c["y"])): 0.0 for c in cells}

    seen: set[tuple[tuple[int, int], tuple[int, int]]] = set()
    for cell in cells:
        here = (int(cell["x"]), int(cell["y"]))
        for other in neighbors(here[0], here[1], width, height):
            edge = tuple(sorted((here, other)))
            if edge in seen:
                continue
            seen.add(edge)
            a = float(lookup[here]["nutrients"])
            b = float(lookup[other]["nutrients"])
            flow = (a - b) * rate
            delta[here] -= flow
            delta[other] += flow

    for xy, change in delta.items():
        lookup[xy]["nutrients"] = max(0.0, float(lookup[xy]["nutrients"]) + change)
