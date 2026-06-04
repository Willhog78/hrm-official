
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any
import time

def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(x)))

@dataclass
class AgentState:
    id: str
    x: float
    y: float
    faction: str = "neutral"
    stress: float = 0.35
    trust: float = 0.55
    health: float = 0.85
    fear: float = 0.25
    valence: float = 0.50
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
        }
