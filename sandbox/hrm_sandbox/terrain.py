"""Procedural terrain: elevation + moisture value noise -> water / grass / forest / rock."""
from __future__ import annotations

import random

WATER, GRASS, FOREST, ROCK = 0, 1, 2, 3


def _smooth(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _value_noise(rng: random.Random, w: int, h: int, scale: int) -> list[list[float]]:
    gw, gh = w // scale + 2, h // scale + 2
    grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]
    out = [[0.0] * w for _ in range(h)]
    for y in range(h):
        gy, fy = divmod(y / scale, 1.0)
        gy = int(gy)
        sy = _smooth(fy)
        for x in range(w):
            gx, fx = divmod(x / scale, 1.0)
            gx = int(gx)
            sx = _smooth(fx)
            top = grid[gy][gx] * (1 - sx) + grid[gy][gx + 1] * sx
            bot = grid[gy + 1][gx] * (1 - sx) + grid[gy + 1][gx + 1] * sx
            out[y][x] = top * (1 - sy) + bot * sy
    return out


def _octaves(rng: random.Random, w: int, h: int) -> list[list[float]]:
    layers = [(_value_noise(rng, w, h, s), wt) for s, wt in ((16, 0.6), (8, 0.3), (4, 0.1))]
    field = [[sum(layer[y][x] * wt for layer, wt in layers) for x in range(w)] for y in range(h)]
    lo = min(min(r) for r in field)
    hi = max(max(r) for r in field)
    span = (hi - lo) or 1.0
    return [[(v - lo) / span for v in row] for row in field]


def generate(rng: random.Random, w: int, h: int) -> list[list[int]]:
    elev = _octaves(rng, w, h)
    moist = _octaves(rng, w, h)
    terrain = [[GRASS] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            e, m = elev[y][x], moist[y][x]
            if e < 0.30:
                terrain[y][x] = WATER
            elif e > 0.74:
                terrain[y][x] = ROCK
            elif m > 0.55:
                terrain[y][x] = FOREST
    return terrain
