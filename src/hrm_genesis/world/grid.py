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
                    "terrain_relief": 0.0,
                    "rock_exposure": 0.0,
                    "terrain_cover": 0.0,
                }
            )

    lookup = {(int(cell["x"]), int(cell["y"])): cell for cell in cells}
    for cell in cells:
        x, y = int(cell["x"]), int(cell["y"])
        adjacent = neighbors(x, y, width, height)
        relief = max(
            (abs(float(cell["elevation"]) - float(lookup[xy]["elevation"])) for xy in adjacent),
            default=0.0,
        )
        elevation_factor = min(1.0, max(0.0, (float(cell["elevation"]) - 35.0) / 45.0))
        relief_factor = min(1.0, relief / 28.0)
        rock_exposure = min(1.0, 0.35 * elevation_factor + 0.65 * relief_factor)

        # Terrain cover is terrain-derived, not independently scattered.
        # Strong relief plus exposed rock can create cave/overhang-like shelter.
        shelter = 0.0
        if rock_exposure >= 0.88 and relief >= 30.0:
            shelter = min(
                0.85,
                0.35 + (rock_exposure - 0.88) * 2.5 + (relief - 30.0) / 60.0,
            )

        cell["terrain_relief"] = round(relief, 6)
        cell["rock_exposure"] = round(rock_exposure, 6)
        cell["terrain_cover"] = round(max(0.0, shelter), 6)

    return cells


def by_coordinate(cells: Iterable[dict]) -> dict[tuple[int, int], dict]:
    return {(int(cell["x"]), int(cell["y"])): cell for cell in cells}
