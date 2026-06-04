
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import random, math, json
from pathlib import Path
from .state import AgentState, WorldState, clamp

@dataclass
class KernelConfig:
    population: int = 250
    seed: int = 42
    width: int = 100
    height: int = 100
    faction_count: int = 5

class HRMKernel:
    """Generic HRM kernel. No frontend. No Jackson. No Simfeld.

    This is the stable engine interface apps should use:
    - create_world()
    - inject_event({...})
    - tick()
    - export_state()
    """
    def __init__(self, config: Optional[KernelConfig] = None):
        self.config = config or KernelConfig()
        self.rng = random.Random(self.config.seed)
        self.state = WorldState(seed=self.config.seed, width=self.config.width, height=self.config.height)
        self.create_world()

    def create_world(self) -> WorldState:
        c = self.config
        self.state.agents = []
        for i in range(c.population):
            faction = f"faction_{i % max(1, c.faction_count)}"
            self.state.agents.append(AgentState(
                id=f"agent_{i:05d}",
                x=self.rng.uniform(0, c.width), y=self.rng.uniform(0, c.height), faction=faction,
                stress=self.rng.uniform(0.20, 0.55), trust=self.rng.uniform(0.35, 0.75),
                health=self.rng.uniform(0.70, 1.0), fear=self.rng.uniform(0.10, 0.45), valence=self.rng.uniform(0.35, 0.70)
            ))
        self.state.zones = [
            {"id":"center", "x":50, "y":50, "radius":22, "pressure":0.25, "label":"central pressure zone"},
            {"id":"edge", "x":18, "y":75, "radius":16, "pressure":0.12, "label":"low-resource edge zone"},
        ]
        self.state.institutions = [
            {"id":"institution_0", "x":50, "y":50, "capacity":0.70, "legitimacy":0.60},
            {"id":"institution_1", "x":25, "y":30, "capacity":0.45, "legitimacy":0.52},
        ]
        return self.state

    def inject_event(self, event: Dict[str, Any]) -> None:
        e = dict(event)
        e.setdefault("tick", self.state.tick)
        e.setdefault("radius", 20)
        e.setdefault("x", 50)
        e.setdefault("y", 50)
        e.setdefault("stress_delta", 0.05)
        e.setdefault("trust_delta", -0.03)
        e.setdefault("health_delta", 0.0)
        e.setdefault("label", "external_event")
        self.state.events.append(e)
        self._apply_event(e)

    def _apply_event(self, e: Dict[str, Any]) -> None:
        ex, ey, radius = float(e["x"]), float(e["y"]), max(1.0, float(e["radius"]))
        for a in self.state.agents:
            d = math.hypot(a.x - ex, a.y - ey)
            if d <= radius:
                weight = 1.0 - (d / radius)
                a.stress = clamp(a.stress + float(e.get("stress_delta",0))*weight)
                a.trust = clamp(a.trust + float(e.get("trust_delta",0))*weight)
                a.health = clamp(a.health + float(e.get("health_delta",0))*weight)
                a.fear = clamp(a.fear + max(0.0, float(e.get("stress_delta",0))) * 0.45 * weight)
                a.valence = clamp(a.valence - max(0.0, float(e.get("stress_delta",0))) * 0.25 * weight)
                a.memory.append({"tick": self.state.tick, "event": e.get("label"), "impact": round(weight,3)})
                if len(a.memory) > 20: a.memory.pop(0)

    def tick(self, steps: int = 1) -> WorldState:
        for _ in range(max(1, int(steps))):
            self.state.tick += 1
            for a in self.state.agents:
                # Motion: bounded random drift. Apps can replace with spatial adapters later.
                a.x = max(0, min(self.config.width, a.x + self.rng.uniform(-1.4, 1.4)))
                a.y = max(0, min(self.config.height, a.y + self.rng.uniform(-1.4, 1.4)))
                # Homeostatic recovery / drift.
                a.stress = clamp(a.stress * 0.985 + 0.20 * 0.015)
                a.fear = clamp(a.fear * 0.982 + 0.12 * 0.018)
                a.trust = clamp(a.trust * 0.996 + 0.50 * 0.004)
                a.health = clamp(a.health * 0.999 + 0.90 * 0.001)
                a.valence = clamp(a.valence * 0.992 + 0.50 * 0.008)
        return self.state

    def export_state(self) -> Dict[str, Any]:
        return self.state.to_dict()

    def save_state(self, path: str | Path) -> Path:
        p = Path(path); p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.export_state(), indent=2), encoding="utf-8")
        return p
