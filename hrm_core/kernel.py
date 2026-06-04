from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import json
import math
import random

from .state import AgentState, WorldState, clamp


@dataclass
class KernelConfig:
    population: int = 250
    seed: int = 42
    width: int = 100
    height: int = 100
    faction_count: int = 5

    # Cognition tuning
    memory_limit: int = 30
    memory_window_ticks: int = 500
    max_memory_amplification: float = 0.75
    recovery_scar_strength: float = 0.50


class HRMKernel:
    """Generic HRM kernel. No frontend. No Jackson. No Simfeld.

    Stable engine interface:
    - create_world()
    - inject_event({...})
    - tick()
    - export_state()

    Cognition v0.2:
    - Agents remember event labels.
    - Similar negative memories amplify future stress/fear/trust reactions.
    - Repeated negative memories slow emotional recovery.
    """

    def __init__(self, config: Optional[KernelConfig] = None):
        self.config = config or KernelConfig()
        self.rng = random.Random(self.config.seed)
        self.state = WorldState(
            seed=self.config.seed,
            width=self.config.width,
            height=self.config.height,
        )
        self.create_world()

    def create_world(self) -> WorldState:
        c = self.config
        self.state.agents = []

        for i in range(c.population):
            faction = f"faction_{i % max(1, c.faction_count)}"
            self.state.agents.append(
                AgentState(
                    id=f"agent_{i:05d}",
                    x=self.rng.uniform(0, c.width),
                    y=self.rng.uniform(0, c.height),
                    faction=faction,
                    stress=self.rng.uniform(0.20, 0.55),
                    trust=self.rng.uniform(0.35, 0.75),
                    health=self.rng.uniform(0.70, 1.0),
                    fear=self.rng.uniform(0.10, 0.45),
                    valence=self.rng.uniform(0.35, 0.70),
                )
            )

        self.state.zones = [
            {
                "id": "center",
                "x": 50,
                "y": 50,
                "radius": 22,
                "pressure": 0.25,
                "label": "central pressure zone",
            },
            {
                "id": "edge",
                "x": 18,
                "y": 75,
                "radius": 16,
                "pressure": 0.12,
                "label": "low-resource edge zone",
            },
        ]

        self.state.institutions = [
            {"id": "institution_0", "x": 50, "y": 50, "capacity": 0.70, "legitimacy": 0.60},
            {"id": "institution_1", "x": 25, "y": 30, "capacity": 0.45, "legitimacy": 0.52},
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

    def _similar_negative_memory_count(self, agent: AgentState, event_label: str) -> int:
        """Count recent memories of the same event label that had negative impact."""
        min_tick = self.state.tick - self.config.memory_window_ticks
        count = 0

        for memory in agent.memory:
            if memory.get("tick", -1) < min_tick:
                continue

            same_event = memory.get("event") == event_label
            negative = bool(memory.get("negative", False))

            if same_event and negative:
                count += 1

        return count

    def _memory_amplification(self, agent: AgentState, event_label: str) -> float:
        """Return multiplier based on similar negative memories."""
        count = self._similar_negative_memory_count(agent, event_label)

        if count <= 0:
            return 1.0

        bonus = min(self.config.max_memory_amplification, count * 0.25)
        return 1.0 + bonus

    def _agent_scar_load(self, agent: AgentState) -> float:
        """Return 0..1 measure of recent negative memory burden."""
        min_tick = self.state.tick - self.config.memory_window_ticks
        negative_count = 0

        for memory in agent.memory:
            if memory.get("tick", -1) >= min_tick and memory.get("negative", False):
                negative_count += 1

        return clamp(negative_count / 6.0)

    def _apply_event(self, e: Dict[str, Any]) -> None:
        ex = float(e["x"])
        ey = float(e["y"])
        radius = max(1.0, float(e["radius"]))
        label = str(e.get("label", "external_event"))

        base_stress_delta = float(e.get("stress_delta", 0.0))
        base_trust_delta = float(e.get("trust_delta", 0.0))
        base_health_delta = float(e.get("health_delta", 0.0))

        is_negative_event = (
            base_stress_delta > 0.0
            or base_trust_delta < 0.0
            or base_health_delta < 0.0
        )

        for agent in self.state.agents:
            distance = math.hypot(agent.x - ex, agent.y - ey)

            if distance > radius:
                continue

            spatial_weight = 1.0 - (distance / radius)

            memory_multiplier = (
                self._memory_amplification(agent, label)
                if is_negative_event
                else 1.0
            )

            stress_delta = base_stress_delta * spatial_weight
            trust_delta = base_trust_delta * spatial_weight
            health_delta = base_health_delta * spatial_weight

            if base_stress_delta > 0.0:
                stress_delta *= memory_multiplier

            if base_trust_delta < 0.0:
                trust_delta *= memory_multiplier

            if base_health_delta < 0.0:
                health_delta *= memory_multiplier

            fear_delta = max(0.0, base_stress_delta) * 0.45 * spatial_weight
            valence_delta = -max(0.0, base_stress_delta) * 0.25 * spatial_weight

            if is_negative_event:
                fear_delta *= memory_multiplier
                valence_delta *= memory_multiplier

            agent.stress = clamp(agent.stress + stress_delta)
            agent.trust = clamp(agent.trust + trust_delta)
            agent.health = clamp(agent.health + health_delta)
            agent.fear = clamp(agent.fear + fear_delta)
            agent.valence = clamp(agent.valence + valence_delta)

            agent.memory.append(
                {
                    "tick": self.state.tick,
                    "event": label,
                    "impact": round(spatial_weight, 3),
                    "negative": is_negative_event,
                    "memory_multiplier": round(memory_multiplier, 3),
                    "stress_delta": round(stress_delta, 4),
                    "trust_delta": round(trust_delta, 4),
                    "fear_delta": round(fear_delta, 4),
                }
            )

            if len(agent.memory) > self.config.memory_limit:
                agent.memory.pop(0)

    def tick(self, steps: int = 1) -> WorldState:
        for _ in range(max(1, int(steps))):
            self.state.tick += 1

            for agent in self.state.agents:
                # Motion: bounded random drift.
                agent.x = max(
                    0,
                    min(self.config.width, agent.x + self.rng.uniform(-1.4, 1.4)),
                )
                agent.y = max(
                    0,
                    min(self.config.height, agent.y + self.rng.uniform(-1.4, 1.4)),
                )

                # Recent negative memories slow emotional recovery.
                scar_load = self._agent_scar_load(agent)
                recovery_drag = 1.0 - (scar_load * self.config.recovery_scar_strength)

                stress_recovery_rate = 0.015 * recovery_drag
                fear_recovery_rate = 0.018 * recovery_drag
                trust_recovery_rate = 0.004 * recovery_drag
                valence_recovery_rate = 0.008 * recovery_drag

                # Homeostatic recovery / drift.
                agent.stress = clamp(agent.stress * (1.0 - stress_recovery_rate) + 0.20 * stress_recovery_rate)
                agent.fear = clamp(agent.fear * (1.0 - fear_recovery_rate) + 0.12 * fear_recovery_rate)
                agent.trust = clamp(agent.trust * (1.0 - trust_recovery_rate) + 0.50 * trust_recovery_rate)
                agent.health = clamp(agent.health * 0.999 + 0.90 * 0.001)
                agent.valence = clamp(agent.valence * (1.0 - valence_recovery_rate) + 0.50 * valence_recovery_rate)

        return self.state

    def export_state(self) -> Dict[str, Any]:
        return self.state.to_dict()

    def save_state(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.export_state(), indent=2), encoding="utf-8")
        return p