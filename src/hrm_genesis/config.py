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
        if self.multi_population_enabled and not self.human_actions_enabled:
            raise ValueError("multi_population_enabled requires human_actions_enabled")

    @property
    def contract_dt(self) -> Fraction:
        return Fraction(self.contract_dt_numerator, self.contract_dt_denominator)

    def canonical(self) -> dict[str, object]:
        return {
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
            "world_width": self.world_width,
            "world_height": self.world_height,
            "ticks_per_year": self.ticks_per_year,
            "genesis_phase": "G8" if self.multi_population_enabled else ("G7" if self.human_actions_enabled else ("G6" if self.human_cognition_enabled else ("G5" if self.human_biology_enabled else ("G3" if self.consumer_ecology_enabled else "G2")))),
        }

    def fingerprint(self) -> str:
        return digest_obj(self.canonical())
