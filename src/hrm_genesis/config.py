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

    def __post_init__(self) -> None:
        if not self.master_seed:
            raise ValueError("master_seed required")
        if self.contract_dt_numerator <= 0 or self.contract_dt_denominator <= 0:
            raise ValueError("contract_dt must be positive")
        if self.max_parallel_domains < 1:
            raise ValueError("max_parallel_domains must be >= 1")

    @property
    def contract_dt(self) -> Fraction:
        return Fraction(self.contract_dt_numerator, self.contract_dt_denominator)

    def canonical(self) -> dict[str, object]:
        return {
            "master_seed": self.master_seed,
            "contract_dt_numerator": self.contract_dt_numerator,
            "contract_dt_denominator": self.contract_dt_denominator,
            "max_parallel_domains": self.max_parallel_domains,
            "genesis_phase": "G0",
        }

    def fingerprint(self) -> str:
        return digest_obj(self.canonical())
