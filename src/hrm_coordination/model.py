from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Mapping, Sequence
import hashlib
import json

JSONScalar = str | int | float | bool | None
JSONValue = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_obj(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, order=True)
class ResourceRef:
    authority_id: str
    resource_id: str

    def as_key(self) -> str:
        return f"{self.authority_id}:{self.resource_id}"


@dataclass(frozen=True)
class ReadVersion:
    ref: ResourceRef
    version: int


@dataclass(frozen=True)
class Mutation:
    ref: ResourceRef
    expected_version: int
    new_value: JSONValue

    def canonical(self) -> dict[str, Any]:
        return {
            "authority_id": self.ref.authority_id,
            "resource_id": self.ref.resource_id,
            "expected_version": self.expected_version,
            "new_value": self.new_value,
        }


@dataclass(frozen=True)
class ProvenanceContribution:
    # Authoritative provenance is infrastructure-owned. `causal_parents` are IDs of
    # prior ledger records/transactions, not agent beliefs or narrative claims.
    causal_parents: tuple[str, ...] = ()
    source_authority: str | None = None
    operation: str = "STATE_CHANGE"

    def canonical(self) -> dict[str, Any]:
        return {
            "causal_parents": list(self.causal_parents),
            "source_authority": self.source_authority,
            "operation": self.operation,
        }


@dataclass(frozen=True)
class TransactionProposal:
    proposal_id: str
    transaction_id: str
    proposer_id: str
    logical_epoch: int
    mutations: tuple[Mutation, ...]
    provenance: ProvenanceContribution = field(default_factory=ProvenanceContribution)
    fallible_claims: Mapping[str, JSONValue] = field(default_factory=dict)

    def conflict_keys(self) -> tuple[str, ...]:
        return tuple(sorted(m.ref.as_key() for m in self.mutations))

    def canonical(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "transaction_id": self.transaction_id,
            "proposer_id": self.proposer_id,
            "logical_epoch": self.logical_epoch,
            "mutations": [m.canonical() for m in sorted(self.mutations, key=lambda x: x.ref.as_key())],
            "provenance": self.provenance.canonical(),
            "fallible_claims": dict(self.fallible_claims),
        }

    def digest(self) -> str:
        return digest_obj(self.canonical())


@dataclass(frozen=True)
class ProposalResult:
    proposal_id: str
    transaction_id: str
    status: str
    reason: str | None = None

    def canonical(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommittedMutation:
    ref: ResourceRef
    before_version: int
    after_version: int
    new_value: JSONValue

    def canonical(self) -> dict[str, Any]:
        return {
            "authority_id": self.ref.authority_id,
            "resource_id": self.ref.resource_id,
            "before_version": self.before_version,
            "after_version": self.after_version,
            "new_value": self.new_value,
        }


@dataclass(frozen=True)
class ResolutionBatch:
    epoch: int
    results: tuple[ProposalResult, ...]
    committed: tuple[CommittedMutation, ...]
    arbitration_digest: str

    def canonical(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "results": [r.canonical() for r in self.results],
            "committed": [m.canonical() for m in self.committed],
            "arbitration_digest": self.arbitration_digest,
        }
