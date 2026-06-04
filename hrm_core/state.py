from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List
import time


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))


@dataclass
class AgentState:
    id: str
    x: float
    y: float
    faction: str = "neutral"

    # Immediate emotional / physical cognition state.
    stress: float = 0.35
    trust: float = 0.55
    health: float = 0.85
    fear: float = 0.25
    valence: float = 0.50

    # Individual homeostatic baselines. Recovery moves toward these personal
    # baselines, not toward one universal population constant. Trauma then
    # modifies these targets into chronic scarred baselines.
    baseline_stress: float = 0.35
    baseline_trust: float = 0.55
    baseline_fear: float = 0.25
    baseline_valence: float = 0.50

    # Persistent cognition state.
    # trauma_load is accumulated negative emotional injury. Unlike memory burden,
    # it decays slowly and survives beyond the short memory amplification window.
    trauma_load: float = 0.0

    # trust_damage is persistent trust scarring caused by negative trust events.
    # It decays more slowly than stress/fear trauma by design.
    trust_damage: float = 0.0

    # resilience protects against trauma formation and recovery drag.
    # Higher resilience means less trauma accumulation and faster recovery.
    resilience: float = 0.50

    # Cognition v0.5: learned appraisal expectations.
    # These are not emotions. They are learned interpretive priors.
    # threat_expectation makes ambiguous threat cues feel more threatening.
    # trust_expectation makes ambiguous trust/betrayal cues feel less safe.
    threat_expectation: float = 0.0
    trust_expectation: float = 0.0

    # Event memory supports cognition v0.2 memory amplification.
    memory: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorldState:
    tick: int = 0
    seed: int = 42
    width: int = 100
    height: int = 100
    agents: List[AgentState] = field(default_factory=list)
    zones: List[Dict[str, Any]] = field(default_factory=list)
    institutions: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "seed": self.seed,
            "width": self.width,
            "height": self.height,
            "agents": [a.to_dict() for a in self.agents],
            "zones": self.zones,
            "institutions": self.institutions,
            "events": self.events[-100:],
            "created_at": self.created_at,
            "metrics": self.metrics(),
        }

    def metrics(self) -> Dict[str, float]:
        n = max(1, len(self.agents))
        return {
            "population": len(self.agents),
            "avg_stress": sum(a.stress for a in self.agents) / n,
            "avg_trust": sum(a.trust for a in self.agents) / n,
            "avg_health": sum(a.health for a in self.agents) / n,
            "avg_fear": sum(a.fear for a in self.agents) / n,
            "avg_valence": sum(a.valence for a in self.agents) / n,
            "avg_trauma_load": sum(a.trauma_load for a in self.agents) / n,
            "avg_trust_damage": sum(a.trust_damage for a in self.agents) / n,
            "avg_resilience": sum(a.resilience for a in self.agents) / n,
            "avg_threat_expectation": sum(a.threat_expectation for a in self.agents) / n,
            "avg_trust_expectation": sum(a.trust_expectation for a in self.agents) / n,
        }
