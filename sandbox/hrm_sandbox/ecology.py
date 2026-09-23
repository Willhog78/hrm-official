"""Non-human world: seasons, berry bushes, nut trees, loose objects, rabbits.

Objects are property bundles (hardness, sharpness, length). The `kind` string is
for display only; no human logic branches on it except the perceptual split
between edible nuts and everything else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import random

from .terrain import WATER, GRASS, FOREST, ROCK

YEAR = 200  # ticks per year; four 50-tick seasons
SEASONS = ("spring", "summer", "autumn", "winter")
BERRY_GROWTH = (0.02, 0.035, 0.012, 0.0)
RABBIT_BREED = (0.012, 0.009, 0.004, 0.0)
NUT_DROP = (0.0, 0.0, 0.08, 0.0)
NUT_LIFETIME = 260
BERRY_CAP = 6.0


def season_of(tick: int) -> int:
    return (tick % YEAR) * 4 // YEAR


@dataclass(eq=False)
class Item:
    id: int
    kind: str
    x: int
    y: int
    hardness: float
    sharpness: float = 0.0
    length: float = 0.0
    born: int = 0
    on_ground: bool = False


@dataclass(eq=False)
class Bush:
    x: int
    y: int
    berries: float = 3.0


@dataclass(eq=False)
class Rabbit:
    x: int
    y: int
    alive: bool = True


@dataclass
class Ecology:
    w: int
    h: int
    terrain: list[list[int]]
    rng: random.Random
    bushes: list[Bush] = field(default_factory=list)
    bush_at: dict[tuple[int, int], Bush] = field(default_factory=dict)
    trees: list[tuple[int, int]] = field(default_factory=list)
    items: dict[tuple[int, int], list[Item]] = field(default_factory=dict)
    rabbits: list[Rabbit] = field(default_factory=list)
    rabbit_cap: int = 320
    _next_item: int = 0

    # --- setup -----------------------------------------------------------
    def populate(self) -> None:
        rng = self.rng
        for y in range(self.h):
            for x in range(self.w):
                t = self.terrain[y][x]
                if t == GRASS and rng.random() < 0.07:
                    self._add_bush(x, y)
                elif t == FOREST:
                    if rng.random() < 0.04:
                        self._add_bush(x, y)
                    elif rng.random() < 0.10:
                        self.trees.append((x, y))
                    if rng.random() < 0.08:
                        self.spawn("stick", x, y, 0)
                elif t == ROCK and rng.random() < 0.5:
                    self.spawn("stone", x, y, 0)
                if t in (GRASS, FOREST) and self._near(x, y, ROCK, 1) and rng.random() < 0.25:
                    self.spawn("stone", x, y, 0)
        land = [(x, y) for y in range(self.h) for x in range(self.w) if self.terrain[y][x] == GRASS]
        for _ in range(160):
            x, y = rng.choice(land)
            self.rabbits.append(Rabbit(x, y))

    def _add_bush(self, x: int, y: int) -> None:
        b = Bush(x, y, self.rng.uniform(1, BERRY_CAP))
        self.bushes.append(b)
        self.bush_at[(x, y)] = b

    def _near(self, x: int, y: int, kind: int, r: int) -> bool:
        for yy in range(max(0, y - r), min(self.h, y + r + 1)):
            for xx in range(max(0, x - r), min(self.w, x + r + 1)):
                if self.terrain[yy][xx] == kind:
                    return True
        return False

    # --- objects ---------------------------------------------------------
    def spawn(self, kind: str, x: int, y: int, tick: int, **props: float) -> Item:
        rng = self.rng
        self._next_item += 1
        if kind == "stone":
            item = Item(self._next_item, kind, x, y, rng.uniform(5.5, 8.0), rng.uniform(0.0, 0.15), rng.uniform(0.1, 0.3), tick)
        elif kind == "stick":
            item = Item(self._next_item, kind, x, y, rng.uniform(1.5, 2.5), 0.0, rng.uniform(0.8, 1.3), tick)
        elif kind == "nut":
            item = Item(self._next_item, kind, x, y, rng.uniform(3.0, 7.0), 0.0, 0.05, tick)
        else:
            item = Item(self._next_item, kind, x, y, props["hardness"], props["sharpness"], props["length"], tick)
        self.place(item, x, y)
        return item

    def place(self, item: Item, x: int, y: int) -> None:
        item.x, item.y = x, y
        item.on_ground = True
        self.items.setdefault((x, y), []).append(item)

    def remove(self, item: Item) -> None:
        item.on_ground = False
        cell = self.items.get((item.x, item.y))
        if cell and item in cell:
            cell.remove(item)
            if not cell:
                del self.items[(item.x, item.y)]

    def passable(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h and self.terrain[y][x] != WATER

    # --- dynamics --------------------------------------------------------
    def step(self, tick: int) -> None:
        rng = self.rng
        s = season_of(tick)
        g = BERRY_GROWTH[s]
        for b in self.bushes:
            if g:
                b.berries = min(BERRY_CAP, b.berries + g)
            elif b.berries > 0:
                b.berries = max(0.0, b.berries - 0.02)  # winter spoilage
        if NUT_DROP[s]:
            for (x, y) in self.trees:
                if rng.random() < NUT_DROP[s]:
                    nx, ny = x + rng.randint(-1, 1), y + rng.randint(-1, 1)
                    if self.passable(nx, ny):
                        self.spawn("nut", nx, ny, tick)
        if tick % 10 == 0:
            for key in list(self.items):
                cell = self.items[key]
                keep = []
                for i in cell:
                    if i.kind == "nut" and tick - i.born > NUT_LIFETIME:
                        i.on_ground = False
                    else:
                        keep.append(i)
                if keep:
                    self.items[key] = keep
                else:
                    del self.items[key]
        if tick % 25 == 0 and self.trees:
            x, y = rng.choice(self.trees)
            self.spawn("stick", x, y, tick)
        self._rabbits(s)

    def _rabbits(self, s: int) -> None:
        rng = self.rng
        n = len(self.rabbits)
        breed = RABBIT_BREED[s] * max(0.0, 1.0 - n / self.rabbit_cap)
        born: list[Rabbit] = []
        survivors: list[Rabbit] = []
        winter = s == 3
        for r in self.rabbits:
            if not r.alive:
                continue
            if rng.random() < (0.004 if winter else 0.0012):
                r.alive = False
                continue
            if rng.random() < 0.5:
                nx, ny = r.x + rng.randint(-1, 1), r.y + rng.randint(-1, 1)
                if self.passable(nx, ny) and self.terrain[ny][nx] != ROCK:
                    r.x, r.y = nx, ny
            if rng.random() < breed:
                born.append(Rabbit(r.x, r.y))
            survivors.append(r)
        self.rabbits = survivors + born
        if not self.rabbits:
            # recolonisation from off-map
            land = [(x, 0) for x in range(self.w) if self.terrain[0][x] == GRASS]
            if land:
                x, y = rng.choice(land)
                self.rabbits = [Rabbit(x, y), Rabbit(x, y)]
