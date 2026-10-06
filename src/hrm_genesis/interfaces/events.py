from __future__ import annotations

from dataclasses import dataclass

from hrm_coordination.model import ProvenanceContribution


@dataclass(frozen=True)
class GenesisEvent:
    event_id: str
    epoch: int
    source_authority: str
    operation: str

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id required")
        if self.epoch < 0:
            raise ValueError("epoch must be >= 0")
        if not self.source_authority:
            raise ValueError("source_authority required")
        if not self.operation:
            raise ValueError("operation required")

    def provenance(self) -> ProvenanceContribution:
        return ProvenanceContribution(
            causal_parents=(),
            source_authority=self.source_authority,
            operation=self.operation,
        )
