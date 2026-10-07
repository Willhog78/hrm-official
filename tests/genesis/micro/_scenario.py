"""Tiny deterministic worlds for micro-scenario tests.

A scenario builds the smallest world the question needs, clears every pool,
places exactly what the test specifies, and then advances the real Agentus
step (`evolve_agentus_step`). Production code is never patched: the builder
only edits initial state, the way a hand-made fixture would.

World physics that the scenario does not ask about is held neutral: 22 °C,
no rain, no lightning, no fire. Producer and consumer ecology do not advance
between steps unless a test calls them, so a placed pool stays where it was
put except for what Agentus themselves take.
"""

from __future__ import annotations

from copy import deepcopy

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import enable_fresh_tissue
from hrm_genesis.human.biology import evolve_agentus_step

FRACTIONS = {"C": 0.86, "N": 0.08, "K": 0.025, "P": 0.012, "Mg": 0.013, "S": 0.01}
ADULT_AGE = 25 * 365


def el(kg: float) -> dict[str, float]:
    return {s: kg * f for s, f in FRACTIONS.items()}


def mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


class Scenario:
    """A cleared tiny world with one Agentus (more can be added)."""

    def __init__(
        self,
        *,
        width: int = 5,
        height: int = 1,
        seed: str = "micro",
        capacities: bool = False,
        thirst: bool = True,
        physiology: str = "reference-v1",
        cognition: bool = True,
    ) -> None:
        config = GenesisConfig(
            master_seed=seed, world_width=max(2, width), world_height=max(2, height), ticks_per_year=365,
            producer_ecology_enabled=True, consumer_ecology_enabled=True, human_biology_enabled=True,
            human_cognition_enabled=cognition, human_actions_enabled=capacities or cognition,
            material_scale_factor=1000.0, human_calibration_enabled=True,
            agentus_capacities_enabled=capacities, agentus_thirst_enabled=thirst,
            agentus_physiology_version=physiology,
        )
        sim = GenesisSimulation(config)
        self.config = config
        self.cognition = cognition
        self.actions = capacities or cognition
        self.humans = sim.human_state()
        self.producers = sim.ecology_state()
        self.matter = sim.matter_state()
        self.world = sim.world_state()
        consumers = sim.consumer_state()
        if "fresh_elements_kg" not in consumers["carcass_cells"][0]:
            consumers = enable_fresh_tissue(consumers)
        self.consumers = consumers
        self.epoch = 1
        self.profile = self.humans["physiology_profile"]
        self._clear()

    # -- construction -------------------------------------------------------

    def _clear(self) -> None:
        for cell in self.producers["cells"]:
            for pool in ("plant_elements_kg", "seed_elements_kg", "woody_elements_kg", "loose_material_elements_kg",
                         "arranged_material_elements_kg", "detritus_elements_kg"):
                cell[pool] = {s: 0.0 for s in FRACTIONS}
            cell["fire_intensity"] = 0.0
        for cell in self.matter["cells"]:
            cell["surface_water_kg"] = 0.0
            cell["soil_water_kg"] = 0.0
        self.matter.setdefault("lithic_cells", {})
        self.matter["lithic_cells"].clear()
        for cell in self.world["cells"]:
            cell.update(temperature=22.0, precipitation=0.0, lightning=0.0, solar=0.8, terrain_cover=0.0)
        self.consumers["animals"] = []
        for cell in self.consumers["carcass_cells"]:
            cell["elements_kg"] = {s: 0.0 for s in FRACTIONS}
            cell["fresh_elements_kg"] = {s: 0.0 for s in FRACTIONS}
            cell["water_kg"] = 0.0
        if "objects" in self.humans:
            self.humans["objects"] = []
        if not self.humans["humans"]:
            # Very small worlds can be too poor for founders to be seeded;
            # borrow one founder from a larger world with the same flags.
            template = GenesisSimulation(GenesisConfig(**{**self.config.__dict__, "world_width": 8, "world_height": 8}))
            self.humans["humans"] = [deepcopy(template.human_state()["humans"][0])]
            if "objects" in self.humans:
                self.humans["objects"] = []
        self.agent = self.humans["humans"][0]
        self.humans["humans"] = [self.agent]
        self.set_agent(0, 0)

    def set_agent(self, x: int, y: int, **fields) -> dict:
        a = self.agent
        a.update(x=x, y=y, age_ticks=ADULT_AGE, injury=0.0, fatigue=0.0)
        a["energy"] = float(self.profile["energy_capacity_kcal"]) * 0.9
        a["body_water_kg"] = float(self.profile["water_capacity_kg"])
        a.update(fields)
        return a

    def add_agent(self, aid: str, x: int, y: int, **fields) -> dict:
        other = deepcopy(self.agent)
        other["id"] = aid
        other["x"], other["y"] = x, y
        if "cognition" in other:
            cog = deepcopy(other["cognition"])
            cog["affordance_values"] = {}
            cog["trace"] = []
            other["cognition"] = cog
        other.update(fields)
        self.humans["humans"].append(other)
        return other

    def _p(self, x, y):
        return next(c for c in self.producers["cells"] if (c["x"], c["y"]) == (x, y))

    def _m(self, x, y):
        return next(c for c in self.matter["cells"] if (c["x"], c["y"]) == (x, y))

    def carcass(self, x, y):
        return next(c for c in self.consumers["carcass_cells"] if (c["x"], c["y"]) == (x, y))

    def set_water(self, x, y, kg):
        self._m(x, y)["surface_water_kg"] = float(kg)

    def water(self, x, y) -> float:
        m = self._m(x, y)
        return float(m["surface_water_kg"]) + float(m["soil_water_kg"])

    def set_pool(self, x, y, pool, kg):
        self._p(x, y)[pool] = el(kg)

    def pool(self, x, y, pool) -> float:
        return mass(self._p(x, y)[pool])

    def set_fresh_tissue(self, x, y, kg):
        self.carcass(x, y)["fresh_elements_kg"] = el(kg)

    def set_decayed_tissue(self, x, y, kg):
        self.carcass(x, y)["elements_kg"] = el(kg)

    def add_animal(self, aid, species, x, y, energy=40.0, body_kg=0.06):
        animal = {"id": aid, "species": species, "x": x, "y": y, "energy": energy, "age_ticks": 1000,
                  "body_elements_kg": el(body_kg), "body_water_kg": 0.2, "forage_bias": 0.0,
                  "last_forage_success": 0.0, "support_streak": 0, "generation": 0, "last_reproduction_epoch": -10**6}
        self.consumers["animals"].append(animal)
        return animal

    def add_stone(self, x, y, sid, lith="siliceous_fine", m=0.6, s=0.1, e=1.2):
        self.matter["lithic_cells"].setdefault(f"{x},{y}", []).append({"id": sid, "lith": lith, "m": m, "s": s, "e": e})

    def remember(self, x, y, **fields):
        locations = self.agent["cognition"]["memory"].setdefault("locations", {})
        entry = {"last_seen_epoch": self.epoch, "food_kg": 0.0, "water_kg": 0.0}
        entry.update(fields)
        locations[f"{x},{y}"] = entry

    # -- stepping -----------------------------------------------------------

    def step(self, n: int = 1) -> "Scenario":
        for _ in range(n):
            self.humans, self.producers, self.matter, consumers = evolve_agentus_step(
                self.humans, self.producers, self.matter, self.world, self.epoch,
                cognition_enabled=self.cognition, actions_enabled=self.actions, consumer_state=self.consumers,
            )
            if consumers is not None:
                self.consumers = consumers
            self.epoch += 1
            alive = [h for h in self.humans["humans"] if h["id"] == self.agent["id"]]
            self.agent = alive[0] if alive else None
        return self

    @property
    def xy(self) -> tuple[int, int] | None:
        return None if self.agent is None else (int(self.agent["x"]), int(self.agent["y"]))

    def deaths(self) -> list[dict]:
        return list(self.humans.get("death_records", []))
