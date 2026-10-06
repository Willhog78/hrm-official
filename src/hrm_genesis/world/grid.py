from __future__ import annotations

from typing import Iterable

from hrm_coordination.seeds import SeedBank


def cell_id(x: int, y: int) -> str:
    return f"{x},{y}"


def neighbors(x: int, y: int, width: int, height: int) -> tuple[tuple[int, int], ...]:
    out: list[tuple[int, int]] = []
    if x > 0:
        out.append((x - 1, y))
    if x + 1 < width:
        out.append((x + 1, y))
    if y > 0:
        out.append((x, y - 1))
    if y + 1 < height:
        out.append((x, y + 1))
    return tuple(out)


def build_grid(width: int, height: int, seed_bank: SeedBank) -> list[dict[str, float | int]]:
    if width < 2 or height < 2:
        raise ValueError("world dimensions must be >= 2")

    cells: list[dict[str, float | int]] = []
    for y in range(height):
        for x in range(width):
            stream = seed_bank.stream(f"world.terrain.{x}.{y}")
            ridge = 18.0 * (1.0 - abs((x / max(1, width - 1)) - 0.5) * 2.0)
            elevation = max(0.0, 40.0 + ridge + stream.uniform(-22.0, 22.0))
            cells.append(
                {
                    "x": x,
                    "y": y,
                    "elevation": round(elevation, 6),
                    "temperature": 0.0,
                    "solar": 0.0,
                    "precipitation": 0.0,
                    "surface_water": 8.0,
                    "soil_moisture": 45.0,
                    "nutrients": round(80.0 + stream.uniform(-8.0, 8.0), 6),
                }
            )
    return cells


def by_coordinate(cells: Iterable[dict]) -> dict[tuple[int, int], dict]:
    return {(int(cell["x"]), int(cell["y"])): cell for cell in cells}
