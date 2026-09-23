from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence
import copy

from .model import CommittedMutation, JSONValue, TransactionProposal, digest_obj


class ProvenanceError(ValueError):
    pass


@dataclass(frozen=True)
class LedgerRecord:
    record_id: str
    epoch: int
    transaction_id: str
    proposal_id: str
    status: str
    proposal_digest: str
    arbitration_digest: str
    committed: tuple[CommittedMutation, ...]
    causal_parents: tuple[str, ...]
    source_authority: str | None
    operation: str
    fallible_claims: dict[str, JSONValue]
    config_fingerprint: str
    previous_epoch_digest: str
    record_digest: str

    def canonical_without_digest(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "epoch": self.epoch,
            "transaction_id": self.transaction_id,
            "proposal_id": self.proposal_id,
            "status": self.status,
            "proposal_digest": self.proposal_digest,
            "arbitration_digest": self.arbitration_digest,
            "committed": [m.canonical() for m in self.committed],
            "causal_parents": list(self.causal_parents),
            "source_authority": self.source_authority,
            "operation": self.operation,
            "fallible_claims": self.fallible_claims,
            "config_fingerprint": self.config_fingerprint,
            "previous_epoch_digest": self.previous_epoch_digest,
        }

    def canonical(self) -> dict[str, Any]:
        value = self.canonical_without_digest()
        value["record_digest"] = self.record_digest
        return value


@dataclass(frozen=True)
class EpochEvidenceBlock:
    epoch: int
    previous_epoch_digest: str
    record_digests: tuple[str, ...]
    epoch_digest: str

    def canonical_without_digest(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "previous_epoch_digest": self.previous_epoch_digest,
            "record_digests": list(self.record_digests),
        }

    def canonical(self) -> dict[str, Any]:
        out = self.canonical_without_digest()
        out["epoch_digest"] = self.epoch_digest
        return out


@dataclass(frozen=True)
class PreparedLedgerBatch:
    """Fully validated epoch evidence waiting for infallible publication."""

    epoch: int
    records: tuple[LedgerRecord, ...]
    block: EpochEvidenceBlock


class ReplayLedger:
    """Epoch-segmented deterministic replay evidence.

    Records within an epoch are independently hashable against the previous epoch
    root. They do not form one per-event global chain. The epoch root is a
    deterministic hash of sorted record digests, so evidence can be produced by
    independent conflict domains and merged at the synchronization boundary.
    """

    def __init__(self, config_fingerprint: str):
        self.config_fingerprint = config_fingerprint
        self._records: list[LedgerRecord] = []
        self._blocks: list[EpochEvidenceBlock] = []
        self._record_ids: set[str] = set()
        self._transaction_ids: set[str] = set()
        self._genesis: dict[str, dict[str, JSONValue]] = {}

    @property
    def records(self) -> tuple[LedgerRecord, ...]:
        return tuple(self._records)

    @property
    def epoch_blocks(self) -> tuple[EpochEvidenceBlock, ...]:
        return tuple(self._blocks)

    def register_genesis(self, authority_id: str, snapshot: dict[str, JSONValue]) -> None:
        if self._records or self._blocks:
            raise RuntimeError("genesis must be registered before event records")
        if authority_id in self._genesis:
            raise RuntimeError(f"duplicate genesis authority {authority_id}")
        self._genesis[authority_id] = copy.deepcopy(snapshot)

    def _genesis_digest(self) -> str:
        return digest_obj({"genesis": self._genesis, "config": self.config_fingerprint})

    def _record_id_for(self, proposal: TransactionProposal) -> str:
        return f"E{proposal.logical_epoch:012d}:{proposal.transaction_id}:{proposal.proposal_id}"

    def _validate_provenance(self, proposal: TransactionProposal) -> None:
        prov = proposal.provenance
        record_id = self._record_id_for(proposal)
        if not prov.operation or not prov.operation.strip():
            raise ProvenanceError("operation required")
        if record_id in prov.causal_parents or proposal.transaction_id in prov.causal_parents:
            raise ProvenanceError("self provenance edge")
        if len(set(prov.causal_parents)) != len(prov.causal_parents):
            raise ProvenanceError("duplicate causal parent")
        unknown = [p for p in prov.causal_parents if p not in self._record_ids and p not in self._transaction_ids]
        if unknown:
            raise ProvenanceError(f"unknown or same-epoch causal parent(s): {unknown}")

    @property
    def expected_epoch(self) -> int:
        return 0 if not self._blocks else self._blocks[-1].epoch + 1

    def validate_epoch(self, epoch: int) -> None:
        expected = self.expected_epoch
        if epoch != expected:
            raise ProvenanceError(f"epoch {epoch} is not admissible; expected {expected}")

    def validate_transaction_ids(self, proposals: Sequence[TransactionProposal]) -> None:
        tx_ids = [p.transaction_id for p in proposals]
        if len(set(tx_ids)) != len(tx_ids):
            raise ProvenanceError("duplicate transaction_id in batch")
        reused = sorted(set(tx_ids) & self._transaction_ids)
        if reused:
            raise ProvenanceError(f"historical transaction_id reuse: {reused}")

    def validate_proposal(self, proposal: TransactionProposal) -> None:
        self._validate_provenance(proposal)

    def prepare_batch(
        self,
        entries: Sequence[tuple[TransactionProposal, str, str, tuple[CommittedMutation, ...]]],
        *,
        epoch: int | None = None,
    ) -> PreparedLedgerBatch:
        """Validate and construct an epoch evidence block without mutating ledger state.

        Every operation in this method is allowed to reject. Fabric must call it
        before causal publication/materialization. `commit_prepared_batch` is the
        corresponding no-revalidation installation step.
        """
        epochs = {p.logical_epoch for p, _, _, _ in entries}
        if epoch is None:
            if len(epochs) != 1:
                raise ProvenanceError("ledger batch must contain exactly one epoch or receive an explicit epoch")
            epoch = next(iter(epochs))
        elif epochs and epochs != {epoch}:
            raise ProvenanceError("ledger batch proposal epoch mismatch")

        self.validate_epoch(epoch)
        proposals = [p for p, _, _, _ in entries]
        self.validate_transaction_ids(proposals)

        # Revalidate against prior-epoch evidence only. Same-epoch causal provenance
        # is intentionally illegal under the explicit feedback-lag contract.
        for proposal in proposals:
            self._validate_provenance(proposal)
            record_id = self._record_id_for(proposal)
            if record_id in self._record_ids:
                raise ProvenanceError(f"historical record_id reuse: {record_id}")

        previous_epoch_digest = self._blocks[-1].epoch_digest if self._blocks else self._genesis_digest()
        built: list[LedgerRecord] = []
        for proposal, status, arbitration_digest, committed in entries:
            provisional = {
                "record_id": self._record_id_for(proposal),
                "epoch": proposal.logical_epoch,
                "transaction_id": proposal.transaction_id,
                "proposal_id": proposal.proposal_id,
                "status": status,
                "proposal_digest": proposal.digest(),
                "arbitration_digest": arbitration_digest,
                "committed": [m.canonical() for m in committed],
                "causal_parents": list(proposal.provenance.causal_parents),
                "source_authority": proposal.provenance.source_authority,
                "operation": proposal.provenance.operation,
                "fallible_claims": dict(proposal.fallible_claims),
                "config_fingerprint": self.config_fingerprint,
                "previous_epoch_digest": previous_epoch_digest,
            }
            built.append(LedgerRecord(
                record_id=provisional["record_id"],
                epoch=proposal.logical_epoch,
                transaction_id=proposal.transaction_id,
                proposal_id=proposal.proposal_id,
                status=status,
                proposal_digest=provisional["proposal_digest"],
                arbitration_digest=arbitration_digest,
                committed=tuple(committed),
                causal_parents=tuple(proposal.provenance.causal_parents),
                source_authority=proposal.provenance.source_authority,
                operation=proposal.provenance.operation,
                fallible_claims=dict(proposal.fallible_claims),
                config_fingerprint=self.config_fingerprint,
                previous_epoch_digest=previous_epoch_digest,
                record_digest=digest_obj(provisional),
            ))

        built.sort(key=lambda r: (r.proposal_id, r.transaction_id, r.record_id))
        record_digests = tuple(sorted(r.record_digest for r in built))
        block_payload = {
            "epoch": epoch,
            "previous_epoch_digest": previous_epoch_digest,
            "record_digests": list(record_digests),
        }
        block = EpochEvidenceBlock(epoch, previous_epoch_digest, record_digests, digest_obj(block_payload))
        return PreparedLedgerBatch(epoch=epoch, records=tuple(built), block=block)

    def commit_prepared_batch(self, prepared: PreparedLedgerBatch) -> tuple[LedgerRecord, ...]:
        """Install a prevalidated batch without any semantic rejection path."""
        self._blocks.append(prepared.block)
        self._records.extend(prepared.records)
        for rec in prepared.records:
            self._record_ids.add(rec.record_id)
            self._transaction_ids.add(rec.transaction_id)
        return prepared.records

    def append_batch(
        self,
        entries: Sequence[tuple[TransactionProposal, str, str, tuple[CommittedMutation, ...]]],
        *,
        epoch: int | None = None,
    ) -> tuple[LedgerRecord, ...]:
        """Compatibility wrapper for callers that do not need split admission/finalization."""
        return self.commit_prepared_batch(self.prepare_batch(entries, epoch=epoch))

    def digest(self) -> str:
        return self._blocks[-1].epoch_digest if self._blocks else self._genesis_digest()

    def verify_chain(self) -> bool:
        records_by_epoch: dict[int, list[LedgerRecord]] = {}
        seen_ids: set[str] = set()
        seen_tx_ids: set[str] = set()
        for rec in self._records:
            if rec.record_id in seen_ids or rec.transaction_id in seen_tx_ids:
                return False
            seen_ids.add(rec.record_id)
            seen_tx_ids.add(rec.transaction_id)
            if digest_obj(rec.canonical_without_digest()) != rec.record_digest:
                return False
            records_by_epoch.setdefault(rec.epoch, []).append(rec)

        previous = self._genesis_digest()
        covered: set[int] = set()
        expected_epoch = 0
        for block in self._blocks:
            if block.epoch != expected_epoch:
                return False
            expected_epoch += 1
            if block.previous_epoch_digest != previous:
                return False
            recs = records_by_epoch.get(block.epoch, [])
            if any(r.previous_epoch_digest != previous for r in recs):
                return False
            digests = tuple(sorted(r.record_digest for r in recs))
            if digests != block.record_digests:
                return False
            if digest_obj(block.canonical_without_digest()) != block.epoch_digest:
                return False
            covered.add(block.epoch)
            previous = block.epoch_digest
        return covered == set(records_by_epoch)

    def replay_state(self) -> dict[str, dict[str, dict[str, Any]]]:
        state: dict[str, dict[str, dict[str, Any]]] = {
            aid: {rid: {"value": copy.deepcopy(v), "version": 0} for rid, v in values.items()}
            for aid, values in self._genesis.items()
        }
        for rec in sorted(self._records, key=lambda r: (r.epoch, r.proposal_id, r.transaction_id)):
            if rec.status != "COMMITTED":
                continue
            for change in rec.committed:
                bucket = state.setdefault(change.ref.authority_id, {})
                current = bucket.get(change.ref.resource_id)
                if current is None:
                    raise ProvenanceError(f"replay unknown resource {change.ref.as_key()}")
                if current["version"] != change.before_version:
                    raise ProvenanceError(f"replay version discontinuity {change.ref.as_key()}")
                bucket[change.ref.resource_id] = {
                    "value": copy.deepcopy(change.new_value),
                    "version": change.after_version,
                }
        return state

    def fallible_projection(self) -> tuple[dict[str, Any], ...]:
        return tuple(
            {"epoch": rec.epoch, "claim_source": rec.proposal_id, "claims": copy.deepcopy(rec.fallible_claims)}
            for rec in self._records if rec.fallible_claims
        )

    def export(self) -> dict[str, Any]:
        return {
            "config_fingerprint": self.config_fingerprint,
            "genesis": copy.deepcopy(self._genesis),
            "records": [r.canonical() for r in self._records],
            "epoch_blocks": [b.canonical() for b in self._blocks],
        }

    @classmethod
    def from_export(cls, payload: dict[str, Any]) -> "ReplayLedger":
        from .model import ResourceRef, CommittedMutation
        ledger = cls(str(payload["config_fingerprint"]))
        ledger._genesis = copy.deepcopy(dict(payload["genesis"]))
        for raw in payload["records"]:
            committed = tuple(
                CommittedMutation(
                    ResourceRef(str(c["authority_id"]), str(c["resource_id"])),
                    int(c["before_version"]), int(c["after_version"]), copy.deepcopy(c["new_value"])
                ) for c in raw["committed"]
            )
            rec = LedgerRecord(
                record_id=str(raw["record_id"]), epoch=int(raw["epoch"]), transaction_id=str(raw["transaction_id"]),
                proposal_id=str(raw["proposal_id"]), status=str(raw["status"]), proposal_digest=str(raw["proposal_digest"]),
                arbitration_digest=str(raw["arbitration_digest"]), committed=committed,
                causal_parents=tuple(raw["causal_parents"]), source_authority=raw["source_authority"], operation=str(raw["operation"]),
                fallible_claims=copy.deepcopy(dict(raw["fallible_claims"])), config_fingerprint=str(raw["config_fingerprint"]),
                previous_epoch_digest=str(raw["previous_epoch_digest"]), record_digest=str(raw["record_digest"]),
            )
            ledger._records.append(rec); ledger._record_ids.add(rec.record_id); ledger._transaction_ids.add(rec.transaction_id)
        for raw in payload["epoch_blocks"]:
            ledger._blocks.append(EpochEvidenceBlock(
                epoch=int(raw["epoch"]), previous_epoch_digest=str(raw["previous_epoch_digest"]),
                record_digests=tuple(raw["record_digests"]), epoch_digest=str(raw["epoch_digest"])
            ))
        if not ledger.verify_chain():
            raise ProvenanceError("invalid imported ledger chain")
        return ledger
