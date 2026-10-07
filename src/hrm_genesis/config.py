from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from hrm_coordination.model import digest_obj


@dataclass(frozen=True)
class GenesisConfig:
    master_seed: str = "hrm-genesis"
    contract_dt_numerator: int = 1
    contract_dt_denominator: int = 1
    max_parallel_domains: int = 32
    physical_world_enabled: bool = True
    matter_enabled: bool = True
    producer_ecology_enabled: bool = False
    consumer_ecology_enabled: bool = False
    human_biology_enabled: bool = False
    human_cognition_enabled: bool = False
    human_actions_enabled: bool = False
    multi_population_enabled: bool = False
    material_scale_factor: float = 1.0
    human_calibration_enabled: bool = False
    # G10.3 capacity model v1. Off by default; earlier configs, fingerprints
    # and results are unchanged.
    agentus_capacities_enabled: bool = False
    # Experimental ablation of capacity v1: "" or a "+"-joined set of
    # "plant_diet" (no sampling of unknown food kinds), "no_interactions" (no
    # manipulation or capture) and "no_recall" (no travel toward remembered
    # food).
    agentus_capacity_ablation: str = ""
    # Thirst as an interoceptive planning drive (G10.4 baseline correction).
    # On by default wherever Agentus cognition is enabled; set False only to
    # reproduce pre-G10.4 results, whose fingerprints omit this key.
    agentus_thirst_enabled: bool = True
    # G10.6 behavioural/locomotion integrity (baseline correction): partial food
    # anchors a hungry agent, dependents move physically, sleep recovers fatigue.
    # False reproduces pre-G10.6 runs exactly.
    agentus_behavior_integrity_enabled: bool = True
    # Reference physiology (G10.5). "reference-v2" adds fat reserves, lean
    # catabolism, realistic lactation and size^0.75 child metabolism.
    agentus_physiology_version: str = "reference-v1"
    world_width: int = 8
    world_height: int = 8
    ticks_per_year: int = 120

    def __post_init__(self) -> None:
        if not self.master_seed:
            raise ValueError("master_seed required")
        if self.contract_dt_numerator <= 0 or self.contract_dt_denominator <= 0:
            raise ValueError("contract_dt must be positive")
        if self.max_parallel_domains < 1:
            raise ValueError("max_parallel_domains must be >= 1")
        if self.world_width < 2 or self.world_height < 2:
            raise ValueError("world dimensions must be >= 2")
        if self.ticks_per_year < 4:
            raise ValueError("ticks_per_year must be >= 4")
        if self.material_scale_factor < 1.0:
            raise ValueError("material_scale_factor must be >= 1.0")
        if self.human_calibration_enabled and self.ticks_per_year != 365:
            raise ValueError("human_calibration_enabled requires ticks_per_year == 365")
        if self.human_calibration_enabled and self.material_scale_factor < 100.0:
            raise ValueError("human_calibration_enabled requires material_scale_factor >= 100")
        if self.matter_enabled and not self.physical_world_enabled:
            raise ValueError("matter_enabled requires physical_world_enabled in G1.5")
        if self.producer_ecology_enabled and not self.matter_enabled:
            raise ValueError("producer_ecology_enabled requires matter_enabled")
        if self.consumer_ecology_enabled and not self.producer_ecology_enabled:
            raise ValueError("consumer_ecology_enabled requires producer_ecology_enabled")
        if self.human_biology_enabled and not self.consumer_ecology_enabled:
            raise ValueError("human_biology_enabled requires consumer_ecology_enabled")
        if self.human_cognition_enabled and not self.human_biology_enabled:
            raise ValueError("human_cognition_enabled requires human_biology_enabled")
        if self.human_actions_enabled and not self.human_cognition_enabled:
            raise ValueError("human_actions_enabled requires human_cognition_enabled")
        if self.agentus_capacities_enabled and not (self.human_actions_enabled and self.human_calibration_enabled):
            raise ValueError("agentus_capacities_enabled requires human_actions_enabled and human_calibration_enabled")
        if self.agentus_physiology_version not in {"reference-v1", "reference-v2"}:
            raise ValueError("unknown agentus_physiology_version")
        if self.agentus_physiology_version != "reference-v1" and not self.human_calibration_enabled:
            raise ValueError("agentus_physiology_version requires human_calibration_enabled")
        parts = [p for p in self.agentus_capacity_ablation.split("+") if p]
        if not set(parts) <= {"plant_diet", "no_interactions", "no_recall"} or len(parts) != len(set(parts)):
            raise ValueError("unknown agentus_capacity_ablation")
        if self.agentus_capacity_ablation and not self.agentus_capacities_enabled:
            raise ValueError("agentus_capacity_ablation requires agentus_capacities_enabled")
        if self.multi_population_enabled and not self.human_actions_enabled:
            raise ValueError("multi_population_enabled requires human_actions_enabled")

    @property
    def thirst_planning_active(self) -> bool:
        """Thirst needs a planner to act on; it is inert without cognition."""
        return self.agentus_thirst_enabled and self.human_cognition_enabled

    @property
    def behavior_integrity_active(self) -> bool:
        return self.agentus_behavior_integrity_enabled and self.human_biology_enabled

    @property
    def contract_dt(self) -> Fraction:
        return Fraction(self.contract_dt_numerator, self.contract_dt_denominator)

    def canonical(self) -> dict[str, object]:
        canonical = {
            "master_seed": self.master_seed,
            "contract_dt_numerator": self.contract_dt_numerator,
            "contract_dt_denominator": self.contract_dt_denominator,
            "max_parallel_domains": self.max_parallel_domains,
            "physical_world_enabled": self.physical_world_enabled,
            "matter_enabled": self.matter_enabled,
            "producer_ecology_enabled": self.producer_ecology_enabled,
            "consumer_ecology_enabled": self.consumer_ecology_enabled,
            "human_biology_enabled": self.human_biology_enabled,
            "human_cognition_enabled": self.human_cognition_enabled,
            "human_actions_enabled": self.human_actions_enabled,
            "multi_population_enabled": self.multi_population_enabled,
            "material_scale_factor": self.material_scale_factor,
            "human_calibration_enabled": self.human_calibration_enabled,
            "world_width": self.world_width,
            "world_height": self.world_height,
            "ticks_per_year": self.ticks_per_year,
            "genesis_phase": "G8" if self.multi_population_enabled else ("G7" if self.human_actions_enabled else ("G6" if self.human_cognition_enabled else ("G5" if self.human_biology_enabled else ("G3" if self.consumer_ecology_enabled else "G2")))),
        }
        if self.agentus_capacities_enabled:
            # Present only when enabled so earlier fingerprints do not change.
            canonical["agentus_capacities_enabled"] = True
            canonical["agentus_capacity_model"] = "capacity-v2"
        if self.agentus_capacity_ablation:
            canonical["agentus_capacity_ablation"] = self.agentus_capacity_ablation
        if self.thirst_planning_active:
            canonical["agentus_thirst_enabled"] = True
        if self.behavior_integrity_active:
            canonical["agentus_behavior_integrity"] = "g10.6"
        if self.agentus_physiology_version != "reference-v1":
            canonical["agentus_physiology_version"] = self.agentus_physiology_version
        return canonical

    def fingerprint(self) -> str:
        return digest_obj(self.canonical())
