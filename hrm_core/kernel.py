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

    # Cognition v0.2 tuning: short-window memory and reaction amplification.
    memory_limit: int = 30
    memory_window_ticks: int = 500
    max_memory_amplification: float = 0.75
    recovery_scar_strength: float = 0.50

    # Cognition v0.3 tuning: persistent trauma accumulation.
    trauma_gain_strength: float = 0.42
    trauma_decay_rate: float = 0.00045
    trust_damage_gain_strength: float = 0.65
    trust_damage_decay_rate: float = 0.00018

    # Persistent trauma creates chronic emotional floors.
    chronic_stress_strength: float = 0.18
    chronic_fear_strength: float = 0.14
    trust_damage_strength: float = 0.10

    # Persistent trauma slows recovery in addition to recent memory burden.
    trauma_recovery_drag_strength: float = 0.55
    minimum_recovery_drag: float = 0.18

    # Cognition v0.5 tuning: appraisal bias.
    # Expectations are learned interpretive priors. They do not directly change
    # emotion every tick; they change how ambiguous events are perceived.
    expectation_gain_strength: float = 0.50
    expectation_decay_rate: float = 0.00030
    max_appraisal_bias: float = 1.25


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

    Cognition v0.3:
    - Negative experiences accumulate persistent trauma_load.
    - Trust violations accumulate persistent trust_damage.
    - Trauma creates chronic stress/fear floors.
    - Trauma slows stress/fear/trust/valence recovery after repeated harm.
    - Resilience reduces trauma formation and trauma-driven recovery drag.
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
                self._create_agent(
                    agent_id=f"agent_{i:05d}",
                    faction=faction,
                    width=c.width,
                    height=c.height,
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

    def _create_agent(self, agent_id: str, faction: str, width: int, height: int) -> AgentState:
        baseline_stress = self.rng.uniform(0.20, 0.55)
        baseline_trust = self.rng.uniform(0.35, 0.75)
        baseline_fear = self.rng.uniform(0.10, 0.45)
        baseline_valence = self.rng.uniform(0.35, 0.70)

        return AgentState(
            id=agent_id,
            x=self.rng.uniform(0, width),
            y=self.rng.uniform(0, height),
            faction=faction,
            stress=baseline_stress,
            trust=baseline_trust,
            health=self.rng.uniform(0.70, 1.0),
            fear=baseline_fear,
            valence=baseline_valence,
            baseline_stress=baseline_stress,
            baseline_trust=baseline_trust,
            baseline_fear=baseline_fear,
            baseline_valence=baseline_valence,
            trauma_load=0.0,
            trust_damage=0.0,
            resilience=self.rng.uniform(0.25, 0.85),
            threat_expectation=0.0,
            trust_expectation=0.0,
        )

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
        e.setdefault("ambiguity", 0.0)
        e.setdefault("threat_cue", 1.0)
        e.setdefault("trust_cue", 1.0)

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

    def _effective_trauma(self, agent: AgentState) -> float:
        """Trauma effect after resilience protection."""
        return clamp(agent.trauma_load * (1.0 - (agent.resilience * 0.55)))

    def _apply_event(self, e: Dict[str, Any]) -> None:
        ex = float(e["x"])
        ey = float(e["y"])
        radius = max(1.0, float(e["radius"]))
        label = str(e.get("label", "external_event"))

        base_stress_delta = float(e.get("stress_delta", 0.0))
        base_trust_delta = float(e.get("trust_delta", 0.0))
        base_health_delta = float(e.get("health_delta", 0.0))
        ambiguity = clamp(float(e.get("ambiguity", 0.0)))
        threat_cue = clamp(float(e.get("threat_cue", 1.0)))
        trust_cue = clamp(float(e.get("trust_cue", 1.0)))

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

            trauma_sensitivity = 1.0 + (self._effective_trauma(agent) * 0.35)

            threat_appraisal_bias = (
                ambiguity
                * threat_cue
                * agent.threat_expectation
                * self.config.max_appraisal_bias
            )
            trust_appraisal_bias = (
                ambiguity
                * trust_cue
                * agent.trust_expectation
                * self.config.max_appraisal_bias
            )

            threat_appraisal_multiplier = 1.0 + threat_appraisal_bias
            trust_appraisal_multiplier = 1.0 + trust_appraisal_bias

            negative_multiplier = memory_multiplier * trauma_sensitivity if is_negative_event else 1.0

            stress_delta = base_stress_delta * spatial_weight
            trust_delta = base_trust_delta * spatial_weight
            health_delta = base_health_delta * spatial_weight

            if base_stress_delta > 0.0:
                stress_delta *= negative_multiplier * threat_appraisal_multiplier

            if base_trust_delta < 0.0:
                trust_delta *= negative_multiplier * trust_appraisal_multiplier

            if base_health_delta < 0.0:
                health_delta *= negative_multiplier * threat_appraisal_multiplier

            fear_delta = max(0.0, base_stress_delta) * 0.45 * spatial_weight
            valence_delta = -max(0.0, base_stress_delta) * 0.25 * spatial_weight

            if is_negative_event:
                fear_delta *= negative_multiplier * threat_appraisal_multiplier
                valence_delta *= negative_multiplier * max(threat_appraisal_multiplier, trust_appraisal_multiplier)

            old_stress = agent.stress
            old_trust = agent.trust
            old_fear = agent.fear

            agent.stress = clamp(agent.stress + stress_delta)
            agent.trust = clamp(agent.trust + trust_delta)
            agent.health = clamp(agent.health + health_delta)
            agent.fear = clamp(agent.fear + fear_delta)
            agent.valence = clamp(agent.valence + valence_delta)

            actual_stress_gain = max(0.0, agent.stress - old_stress)
            actual_fear_gain = max(0.0, agent.fear - old_fear)
            actual_trust_loss = max(0.0, old_trust - agent.trust)

            trauma_gain = 0.0
            trust_damage_gain = 0.0

            if is_negative_event:
                raw_trauma = (
                    actual_stress_gain * 0.42
                    + actual_fear_gain * 0.38
                    + actual_trust_loss * 0.20
                )
                trauma_gain = raw_trauma * self.config.trauma_gain_strength * (1.0 - agent.resilience * 0.50)
                agent.trauma_load = clamp(agent.trauma_load + trauma_gain)

                if actual_trust_loss > 0.0:
                    trust_damage_gain = (
                        actual_trust_loss
                        * self.config.trust_damage_gain_strength
                        * (1.0 - agent.resilience * 0.35)
                    )
                    agent.trust_damage = clamp(agent.trust_damage + trust_damage_gain)

                threat_expectation_gain = (
                    (actual_stress_gain * 0.55 + actual_fear_gain * 0.45)
                    * self.config.expectation_gain_strength
                    * (1.0 - agent.resilience * 0.30)
                )
                trust_expectation_gain = (
                    actual_trust_loss
                    * self.config.expectation_gain_strength
                    * (1.0 - agent.resilience * 0.25)
                )

                agent.threat_expectation = clamp(agent.threat_expectation + threat_expectation_gain)
                agent.trust_expectation = clamp(agent.trust_expectation + trust_expectation_gain)
            else:
                threat_expectation_gain = 0.0
                trust_expectation_gain = 0.0

            agent.memory.append(
                {
                    "tick": self.state.tick,
                    "event": label,
                    "impact": round(spatial_weight, 3),
                    "negative": is_negative_event,
                    "memory_multiplier": round(memory_multiplier, 3),
                    "trauma_sensitivity": round(trauma_sensitivity, 3),
                    "threat_appraisal_multiplier": round(threat_appraisal_multiplier, 3),
                    "trust_appraisal_multiplier": round(trust_appraisal_multiplier, 3),
                    "threat_expectation": round(agent.threat_expectation, 4),
                    "trust_expectation": round(agent.trust_expectation, 4),
                    "stress_delta": round(stress_delta, 4),
                    "trust_delta": round(trust_delta, 4),
                    "fear_delta": round(fear_delta, 4),
                    "trauma_gain": round(trauma_gain, 5),
                    "trust_damage_gain": round(trust_damage_gain, 5),
                    "threat_expectation_gain": round(threat_expectation_gain, 5),
                    "trust_expectation_gain": round(trust_expectation_gain, 5),
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

                # Persistent trauma decays slowly. Trust damage decays slower.
                agent.trauma_load = clamp(agent.trauma_load * (1.0 - self.config.trauma_decay_rate))
                agent.trust_damage = clamp(agent.trust_damage * (1.0 - self.config.trust_damage_decay_rate))
                agent.threat_expectation = clamp(agent.threat_expectation * (1.0 - self.config.expectation_decay_rate))
                agent.trust_expectation = clamp(agent.trust_expectation * (1.0 - self.config.expectation_decay_rate))

                # Recent negative memories and persistent trauma both slow recovery.
                scar_load = self._agent_scar_load(agent)
                effective_trauma = self._effective_trauma(agent)

                memory_recovery_drag = 1.0 - (scar_load * self.config.recovery_scar_strength)
                trauma_recovery_drag = 1.0 - (effective_trauma * self.config.trauma_recovery_drag_strength)
                recovery_drag = max(
                    self.config.minimum_recovery_drag,
                    memory_recovery_drag * trauma_recovery_drag,
                )

                stress_recovery_rate = 0.015 * recovery_drag
                fear_recovery_rate = 0.018 * recovery_drag
                trust_recovery_rate = 0.004 * recovery_drag
                valence_recovery_rate = 0.008 * recovery_drag

                chronic_stress_target = agent.baseline_stress + (effective_trauma * self.config.chronic_stress_strength)
                chronic_fear_target = agent.baseline_fear + (effective_trauma * self.config.chronic_fear_strength)
                trust_target = agent.baseline_trust - (agent.trust_damage * self.config.trust_damage_strength)
                valence_target = agent.baseline_valence - (effective_trauma * 0.08)

                # Homeostatic recovery / drift. Trauma modifies each agent's own baseline.
                agent.stress = clamp(agent.stress * (1.0 - stress_recovery_rate) + chronic_stress_target * stress_recovery_rate)
                agent.fear = clamp(agent.fear * (1.0 - fear_recovery_rate) + chronic_fear_target * fear_recovery_rate)
                agent.trust = clamp(agent.trust * (1.0 - trust_recovery_rate) + trust_target * trust_recovery_rate)
                agent.health = clamp(agent.health * 0.999 + 0.90 * 0.001)
                agent.valence = clamp(agent.valence * (1.0 - valence_recovery_rate) + valence_target * valence_recovery_rate)

        return self.state

    def export_state(self) -> Dict[str, Any]:
        return self.state.to_dict()

    def save_state(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.export_state(), indent=2), encoding="utf-8")
        return p
