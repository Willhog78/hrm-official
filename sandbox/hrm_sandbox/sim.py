"""Simulation loop: world dynamics, human behaviour, physical outcomes of actions."""
from __future__ import annotations

import random

from .ecology import Ecology, Item, Rabbit
from .humans import (ADULT, INFANT, OLD, HUNGER_RATE, THIRST_RATE, ALPHA, ALPHA_OBS,
                     HAND, Human, sig, category)
from .terrain import WATER, GRASS, generate
from .observer import Observer

PERCEIVE = 5
WATCH = 3
BERRY_FOOD = 15.0
NUT_FOOD = 14.0
RABBIT_FOOD = 60.0


def _cheb(ax: int, ay: int, bx: int, by: int) -> int:
    return max(abs(ax - bx), abs(ay - by))


class Sim:
    def __init__(self, seed: int = 1, w: int = 64, h: int = 40, bands: int = 4,
                 band_size: int = 12, frame_every: int = 10):
        self.seed = seed
        self.w, self.h = w, h
        self.rng = random.Random(seed)
        self.terrain = generate(random.Random(seed * 7919 + 1), w, h)
        self.eco = Ecology(w, h, self.terrain, random.Random(seed * 7919 + 2))
        self.eco.populate()
        self.shore = [[self.terrain[y][x] != WATER and self._touches_water(x, y)
                       for x in range(w)] for y in range(h)]
        self.tick = 0
        self.humans: list[Human] = []
        self.by_id: dict[int, Human] = {}
        self._next_id = 0
        self.observer = Observer(self, frame_every)
        self._seed_bands(bands, band_size)
        self.observer.sample()

    # --- setup -----------------------------------------------------------
    def _touches_water(self, x: int, y: int) -> bool:
        for yy in range(y - 1, y + 2):
            for xx in range(x - 1, x + 2):
                if 0 <= xx < self.w and 0 <= yy < self.h and self.terrain[yy][xx] == WATER:
                    return True
        return False

    def _seed_bands(self, bands: int, size: int) -> None:
        rng = self.rng
        anchors = [(0.22, 0.28), (0.78, 0.28), (0.22, 0.75), (0.78, 0.75),
                   (0.5, 0.5), (0.5, 0.15), (0.5, 0.85), (0.1, 0.5)]
        for b in range(bands):
            ax, ay = anchors[b % len(anchors)]
            cx, cy = self._nearest_land(int(ax * self.w), int(ay * self.h))
            for _ in range(size):
                x, y = self._nearest_land(cx + rng.randint(-2, 2), cy + rng.randint(-2, 2))
                self._add_human(x, y, rng.random() < 0.5, rng.randint(ADULT, 1800), b,
                                rng.uniform(0.04, 0.3), rng.uniform(0.3, 0.9), None)

    def _nearest_land(self, x: int, y: int) -> tuple[int, int]:
        x = min(max(x, 0), self.w - 1)
        y = min(max(y, 0), self.h - 1)
        for r in range(max(self.w, self.h)):
            for yy in range(y - r, y + r + 1):
                for xx in range(x - r, x + r + 1):
                    if (0 <= xx < self.w and 0 <= yy < self.h
                            and self.terrain[yy][xx] == GRASS):
                        return xx, yy
        return x, y

    def _add_human(self, x, y, female, age, band, curiosity, attention, mother) -> Human:
        self._next_id += 1
        hu = Human(self._next_id, x, y, female, age, band, curiosity, attention, mother,
                   hunger=self.rng.uniform(10, 30))
        self.humans.append(hu)
        self.by_id[hu.id] = hu
        return hu

    # --- main loop -------------------------------------------------------
    def run(self, ticks: int) -> None:
        for _ in range(ticks):
            self.step()

    def step(self) -> None:
        self.tick += 1
        self.eco.step(self.tick)
        self.rabbit_at: dict[tuple[int, int], list[Rabbit]] = {}
        for r in self.eco.rabbits:
            if r.alive:
                self.rabbit_at.setdefault((r.x, r.y), []).append(r)
        self.human_at: dict[tuple[int, int], list[Human]] = {}
        for hu in self.humans:
            self.human_at.setdefault((hu.x, hu.y), []).append(hu)
        order = list(self.humans)
        self.rng.shuffle(order)
        for hu in order:
            if hu.alive:
                self._live(hu)
        if self.tick % 10 == 0:
            self._update_familiarity()
        self.humans = [hu for hu in self.humans if hu.alive]
        self.observer.sample()

    def _update_familiarity(self) -> None:
        for hu in self.humans:
            for other in self._near_humans(hu.x, hu.y, 2):
                if other is not hu:
                    hu.familiar[other.id] = hu.familiar.get(other.id, 0) + 1

    def _near_humans(self, x: int, y: int, r: int):
        for yy in range(y - r, y + r + 1):
            for xx in range(x - r, x + r + 1):
                for other in self.human_at.get((xx, yy), ()):
                    if other.alive:
                        yield other

    # --- one human, one tick ---------------------------------------------
    def _live(self, hu: Human) -> None:
        hu.age += 1
        infant = hu.age < INFANT
        hu.hunger += HUNGER_RATE * (0.6 if infant else 1.0)
        hu.thirst += THIRST_RATE * (0.6 if infant else 1.0)
        if hu.hunger >= 100:
            return self._die(hu, "starvation")
        if hu.thirst >= 100:
            return self._die(hu, "thirst")
        if hu.age > OLD and self.rng.random() < 0.0015 * (1 + (hu.age - OLD) / 200):
            return self._die(hu, "old age")
        if infant:
            return self._infant(hu)
        if self._next_to_water(hu) and hu.thirst > 15:
            hu.thirst = 0.0
            return
        hu.plan_timer -= 1
        if hu.target is not None and not self._valid(hu.target):
            hu.target = None
        if hu.target is None or hu.plan_timer <= 0:
            self._perceive(hu)
            hu.target = self._choose(hu)
            hu.plan_timer = 4
        if hu.target is None:
            return self._wander(hu)
        tx, ty = self._target_pos(hu.target)
        if _cheb(hu.x, hu.y, tx, ty) <= (0 if hu.target[0] == "go" else 1):
            self._act(hu, hu.target)
        else:
            self._step_toward(hu, tx, ty)

    def _die(self, hu: Human, cause: str) -> None:
        hu.alive = False
        if hu.held is not None:
            self.eco.place(hu.held, hu.x, hu.y)
            hu.held = None
        self.observer.death(hu, cause)

    def _infant(self, hu: Human) -> None:
        mom = self.by_id.get(hu.mother) if hu.mother else None
        if mom is None or not mom.alive:
            return self._wander(hu)
        if _cheb(hu.x, hu.y, mom.x, mom.y) > 1:
            self._step_toward(hu, mom.x, mom.y)
        elif mom.hunger < 70:  # nursing transfers the mother's reserves
            hu.hunger = max(0.0, hu.hunger - 0.8)
            hu.thirst = max(0.0, hu.thirst - 0.9)
            mom.hunger += 0.25
            mom.thirst += 0.2

    # --- perception & memory ---------------------------------------------
    def _perceive(self, hu: Human) -> None:
        hu.seen_items = []
        hu.seen_rabbits = []
        eco = self.eco
        for y in range(max(0, hu.y - PERCEIVE), min(self.h, hu.y + PERCEIVE + 1)):
            for x in range(max(0, hu.x - PERCEIVE), min(self.w, hu.x + PERCEIVE + 1)):
                pos = (x, y)
                if self.shore[y][x]:
                    hu.mem_shore.add(pos)
                b = eco.bush_at.get(pos)
                if b is not None:
                    hu.mem_bush[pos] = (b.berries, self.tick)
                cell = eco.items.get(pos)
                if cell:
                    hu.seen_items.extend(cell)
                    if any(i.kind == "nut" for i in cell):
                        hu.mem_nuts[pos] = self.tick
                    elif pos in hu.mem_nuts:
                        del hu.mem_nuts[pos]
                elif pos in hu.mem_nuts:
                    del hu.mem_nuts[pos]
                rs = self.rabbit_at.get(pos)
                if rs:
                    hu.seen_rabbits.extend(rs)

    # --- decision ----------------------------------------------------------
    def _choose(self, hu: Human):
        rng = self.rng
        if hu.thirst > 45 or (hu.thirst > 25 and hu.hunger < 30):
            spot = self._nearest(hu, hu.mem_shore)
            return ("go", None, spot[0], spot[1]) if spot else None
        if hu.hunger > 30:
            opts = self._food_options(hu)
            if not opts:
                return None
            if rng.random() < hu.curiosity * 0.25:
                return rng.choice(opts)[1]
            return max(opts, key=lambda o: o[0])[1]
        return self._leisure(hu)

    def _food_options(self, hu: Human) -> list[tuple[float, tuple]]:
        held = sig(hu.held)
        opts: list[tuple[float, tuple]] = []

        def add(value, tgt, x, y):
            d = _cheb(hu.x, hu.y, x, y)
            opts.append((value / (1 + 0.15 * d), tgt))

        for pos, (berries, seen) in hu.mem_bush.items():
            est = berries if self.tick - seen < 100 else 1.5
            if est >= 1:
                add(min(est, 3) * BERRY_FOOD, ("bush", self.eco.bush_at[pos], pos[0], pos[1]), *pos)
        q_nut = hu.qv((held, "strike", "nut"))
        q_rab = hu.qv((held, "strike", "rabbit"))
        nuts_seen = False
        for item in hu.seen_items:
            if item.kind == "nut":
                nuts_seen = True
                add(q_nut, ("nut", item, item.x, item.y), item.x, item.y)
            else:
                cat = category(item)
                for verb in ("strike", "bind"):
                    v = hu.qv((held, verb, cat))
                    if v > 1:
                        add(v, ("use", item, item.x, item.y, verb), item.x, item.y)
                gain = hu.value_of(sig(item)) - hu.value_of(held)
                if gain > 1:
                    add(gain * 0.8, ("take", item, item.x, item.y), item.x, item.y)
        if not nuts_seen:
            for pos in hu.mem_nuts:
                add(q_nut * 0.5, ("go", None, pos[0], pos[1]), *pos)
        for r in hu.seen_rabbits:
            add(q_rab, ("rabbit", r, r.x, r.y), r.x, r.y)
        return opts

    def _leisure(self, hu: Human):
        rng = self.rng
        if rng.random() < hu.curiosity:
            things = [i for i in hu.seen_items if i.kind != "nut"]
            if hu.held is None and things:
                it = rng.choice(things)
                return ("take", it, it.x, it.y)
            pool = [("use", i, i.x, i.y, rng.choice(("strike", "bind"))) for i in things]
            pool += [("nut", i, i.x, i.y) for i in hu.seen_items if i.kind == "nut"]
            pool += [("rabbit", r, r.x, r.y) for r in hu.seen_rabbits]
            if pool:
                return rng.choice(pool)
        if (hu.female and ADULT <= hu.age < 2200 and hu.hunger < 35 and hu.thirst < 40
                and self.tick - hu.last_birth > 350):
            for other in self._near_humans(hu.x, hu.y, 2):
                if not other.female and other.age >= ADULT and rng.random() < 0.02:
                    self._birth(hu, other)
                    break
        mate = self._most_familiar(hu)
        if mate is not None and _cheb(hu.x, hu.y, mate.x, mate.y) > 3:
            return ("go", None, mate.x, mate.y)
        return None

    def _most_familiar(self, hu: Human) -> Human | None:
        best, best_n = None, 0
        for oid, n in hu.familiar.items():
            if n > best_n:
                o = self.by_id.get(oid)
                if o is not None and o.alive:
                    best, best_n = o, n
        return best

    def _birth(self, mom: Human, dad: Human) -> None:
        rng = self.rng
        cur = min(0.5, max(0.01, (mom.curiosity + dad.curiosity) / 2 + rng.gauss(0, 0.04)))
        att = min(1.0, max(0.1, (mom.attention + dad.attention) / 2 + rng.gauss(0, 0.08)))
        kid = self._add_human(mom.x, mom.y, rng.random() < 0.5, 0, mom.band, cur, att, mom.id)
        kid.hunger, kid.thirst = 10.0, 5.0
        kid.familiar[mom.id] = 50
        mom.familiar[kid.id] = 50
        mom.last_birth = self.tick
        mom.hunger += 15
        mom.children += 1
        dad.children += 1
        self.observer.birth(kid)

    # --- targets -----------------------------------------------------------
    def _valid(self, tgt) -> bool:
        kind, obj = tgt[0], tgt[1]
        if kind == "rabbit":
            return obj.alive
        if kind in ("nut", "take", "use"):
            return obj.on_ground
        if kind == "bush":
            return obj.berries >= 1
        return True

    def _target_pos(self, tgt) -> tuple[int, int]:
        if tgt[0] == "rabbit":
            return tgt[1].x, tgt[1].y
        return tgt[2], tgt[3]

    # --- actions & physics -------------------------------------------------
    def _act(self, hu: Human, tgt) -> None:
        kind, obj = tgt[0], tgt[1]
        rng = self.rng
        tool = hu.held or HAND
        held = sig(hu.held)
        if kind == "go":
            hu.target = None
        elif kind == "bush":
            obj.berries -= 1
            hu.hunger = max(0.0, hu.hunger - BERRY_FOOD)
            hu.mem_bush[(obj.x, obj.y)] = (obj.berries, self.tick)
            if hu.hunger < 10 or obj.berries < 1:
                hu.target = None
        elif kind == "nut":
            power = tool.hardness * rng.uniform(0.8, 1.25)
            food = 0.0
            if power >= obj.hardness:
                self.eco.remove(obj)
                hu.hunger = max(0.0, hu.hunger - NUT_FOOD)
                food = NUT_FOOD
            self._learn(hu, (held, "strike", "nut"), food, None)
            hu.target = None
        elif kind == "rabbit":
            chance = 0.1 + 0.45 * tool.sharpness + 0.15 * min(tool.length, 1.5)
            food = 0.0
            if rng.random() < chance:
                obj.alive = False
                food = RABBIT_FOOD
                hu.hunger = max(0.0, hu.hunger - RABBIT_FOOD)
                self._share(hu, RABBIT_FOOD - 30)
            else:
                for _ in range(2):
                    nx, ny = obj.x + rng.randint(-1, 1), obj.y + rng.randint(-1, 1)
                    if self.eco.passable(nx, ny):
                        obj.x, obj.y = nx, ny
            self._learn(hu, (held, "strike", "rabbit"), food, None)
            hu.target = None
        elif kind == "take":
            self.eco.remove(obj)
            if hu.held is not None:
                self.eco.place(hu.held, hu.x, hu.y)
            hu.held = obj
            hu.target = None
        elif kind == "use":
            verb = tgt[4]
            key = (held, verb, category(obj))
            result = None
            if verb == "strike":
                power = tool.hardness * rng.uniform(0.8, 1.25)
                if (hu.held is not None and obj.hardness >= 4 and power >= obj.hardness - 1
                        and rng.random() < 0.5):
                    # conchoidal fracture: a thin, sharp fragment detaches
                    flake = self.eco.spawn("flake", obj.x, obj.y, self.tick,
                                           hardness=obj.hardness,
                                           sharpness=rng.uniform(0.5, 0.9),
                                           length=rng.uniform(0.15, 0.35))
                    result = sig(flake)
            elif verb == "bind" and hu.held is not None and rng.random() < 0.35:
                self.eco.remove(obj)
                a = hu.held
                hu.held = Item(obj.id, "bound", hu.x, hu.y,
                               hardness=max(a.hardness, obj.hardness),
                               sharpness=max(a.sharpness, obj.sharpness),
                               length=min(2.0, a.length + obj.length), born=self.tick)
                result = sig(hu.held)
            self._learn(hu, key, 0.0, result)
            hu.target = None

    def _share(self, hu: Human, surplus: float) -> None:
        """Surplus meat goes to the hungriest nearby familiar people."""
        near = [o for o in self._near_humans(hu.x, hu.y, 2)
                if o is not hu and hu.familiar.get(o.id, 0) > 5 and o.hunger > 20]
        near.sort(key=lambda o: -o.hunger)
        for o in near[:2]:
            give = min(surplus / 2, o.hunger)
            o.hunger -= give

    def _learn(self, actor: Human, key, food: float, result: str | None) -> None:
        if actor.learn(key, food, result, ALPHA, self.tick, actor.id):
            self.observer.learned(actor, key, actor.id)
        for other in self._near_humans(actor.x, actor.y, WATCH):
            if other is actor:
                continue
            p = other.attention * (1.0 if other.familiar.get(actor.id, 0) > 5 else 0.4)
            if other.mother == actor.id:
                p += 0.3
            if self.rng.random() < p:
                if other.learn(key, food, result, ALPHA_OBS, self.tick, actor.id):
                    self.observer.learned(other, key, actor.id)

    # --- movement ------------------------------------------------------------
    def _next_to_water(self, hu: Human) -> bool:
        return self.shore[hu.y][hu.x]

    def _nearest(self, hu: Human, spots) -> tuple[int, int] | None:
        best, bd = None, 10 ** 9
        for (x, y) in spots:
            d = _cheb(hu.x, hu.y, x, y)
            if d < bd:
                best, bd = (x, y), d
        return best

    def _move(self, hu: Human, nx: int, ny: int) -> bool:
        if self.eco.passable(nx, ny):
            hu.x, hu.y = nx, ny
            return True
        return False

    def _step_toward(self, hu: Human, tx: int, ty: int) -> None:
        dx = (tx > hu.x) - (tx < hu.x)
        dy = (ty > hu.y) - (ty < hu.y)
        if self._move(hu, hu.x + dx, hu.y + dy):
            return
        if dx and self._move(hu, hu.x + dx, hu.y):
            return
        if dy and self._move(hu, hu.x, hu.y + dy):
            return
        self._wander(hu)

    def _wander(self, hu: Human) -> None:
        rng = self.rng
        if rng.random() < 0.2:
            hu.heading = (rng.randint(-1, 1), rng.randint(-1, 1))
        for _ in range(4):
            dx, dy = hu.heading
            if self._move(hu, hu.x + dx, hu.y + dy):
                return
            hu.heading = (rng.randint(-1, 1), rng.randint(-1, 1))
