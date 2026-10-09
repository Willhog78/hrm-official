from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence
import copy

from .model import CommittedMutation, JSONValue, TransactionProposal, canonical_json, digest_obj


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
        # IDs (record and transaction) of COMMITTED records only: the only legal
        # causal parents. REJECTED evidence burns IDs but never caused anything.
        self._committed_ids: set[str] = set()
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
        # JSON-encode the id pair so ids containing separators cannot collide
        # (plain "tx:pid" made ("a:b", "c") and ("a", "b:c") identical).
        return f"E{proposal.logical_epoch:012d}:" + canonical_json([proposal.transaction_id, proposal.proposal_id])

    def _validate_provenance(self, proposal: TransactionProposal) -> None:
        prov = proposal.provenance
        record_id = self._record_id_for(proposal)
        if not prov.operation or not prov.operation.strip():
            raise ProvenanceError("operation required")
        if record_id in prov.causal_parents or proposal.transaction_id in prov.causal_parents:
            raise ProvenanceError("self provenance edge")
        if len(set(prov.causal_parents)) != len(prov.causal_parents):
            raise ProvenanceError("duplicate causal parent")
        unknown = [p for p in prov.causal_parents if p not in self._committed_ids]
        if unknown:
            raise ProvenanceError(f"unknown, rejected or same-epoch causal parent(s): {unknown}")

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
        batch_record_ids: set[str] = set()
        # REJECTED entries are evidence that a proposal was refused (including for
        # invalid provenance); they carry no causal effect, so only COMMITTED
        # entries must have admissible provenance.
        for proposal, status, _, _ in entries:
            if status == "COMMITTED":
                self._validate_provenance(proposal)
            record_id = self._record_id_for(proposal)
            if record_id in self._record_ids:
                raise ProvenanceError(f"historical record_id reuse: {record_id}")
            if record_id in batch_record_ids:
                raise ProvenanceError(f"duplicate record_id in batch: {record_id}")
            batch_record_ids.add(record_id)

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
            if rec.status == "COMMITTED":
                self._committed_ids.update((rec.record_id, rec.transaction_id))
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
            if rec.config_fingerprint != self.config_fingerprint:
                return False
            if rec.record_id != f"E{rec.epoch:012d}:" + canonical_json([rec.transaction_id, rec.proposal_id]):
                return False
            seen_ids.add(rec.record_id)
            seen_tx_ids.add(rec.transaction_id)
            if digest_obj(rec.canonical_without_digest()) != rec.record_digest:
                return False
            records_by_epoch.setdefault(rec.epoch, []).append(rec)

        previous = self._genesis_digest()
        committed_before: set[str] = set()
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
            # A committed record may only cite committed records from earlier epochs.
            for r in recs:
                if r.status == "COMMITTED" and any(p not in committed_before for p in r.causal_parents):
                    return False
            for r in recs:
                if r.status == "COMMITTED":
                    committed_before.update((r.record_id, r.transaction_id))
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
        ledger = cls(str(payload["config_fingerprint"]))
        ledger._genesis = copy.deepcopy(dict(payload["genesis"]))
        for raw in payload["records"]:
            rec = _record_from_canonical(raw)
            ledger._records.append(rec); ledger._record_ids.add(rec.record_id); ledger._transaction_ids.add(rec.transaction_id)
            if rec.status == "COMMITTED":
                ledger._committed_ids.update((rec.record_id, rec.transaction_id))
        for raw in payload["epoch_blocks"]:
            ledger._blocks.append(EpochEvidenceBlock(
                epoch=int(raw["epoch"]), previous_epoch_digest=str(raw["previous_epoch_digest"]),
                record_digests=tuple(raw["record_digests"]), epoch_digest=str(raw["epoch_digest"])
            ))
        if not ledger.verify_chain():
            raise ProvenanceError("invalid imported ledger chain")
        return ledger


def _record_from_canonical(raw: dict[str, Any]) -> LedgerRecord:
    from .model import ResourceRef
    committed = tuple(
        CommittedMutation(
            ResourceRef(str(c["authority_id"]), str(c["resource_id"])),
            int(c["before_version"]), int(c["after_version"]), copy.deepcopy(c["new_value"])
        ) for c in raw["committed"]
    )
    return LedgerRecord(
        record_id=str(raw["record_id"]), epoch=int(raw["epoch"]), transaction_id=str(raw["transaction_id"]),
        proposal_id=str(raw["proposal_id"]), status=str(raw["status"]), proposal_digest=str(raw["proposal_digest"]),
        arbitration_digest=str(raw["arbitration_digest"]), committed=committed,
        causal_parents=tuple(raw["causal_parents"]), source_authority=raw["source_authority"], operation=str(raw["operation"]),
        fallible_claims=copy.deepcopy(dict(raw["fallible_claims"])), config_fingerprint=str(raw["config_fingerprint"]),
        previous_epoch_digest=str(raw["previous_epoch_digest"]), record_digest=str(raw["record_digest"]),
    )


def _block_from_canonical(raw: dict[str, Any]) -> EpochEvidenceBlock:
    return EpochEvidenceBlock(
        epoch=int(raw["epoch"]), previous_epoch_digest=str(raw["previous_epoch_digest"]),
        record_digests=tuple(raw["record_digests"]), epoch_digest=str(raw["epoch_digest"]),
    )


class StreamingReplayLedger(ReplayLedger):
    """The same replay evidence, streamed to disk instead of held in RAM.

    Records and blocks are built and digested exactly as by ReplayLedger, so the
    digest chain is identical. Each committed epoch is appended to `path` as one
    gzip member holding one JSON line (`{"epoch", "block", "records"}`); the
    genesis is the first member. Only the last `buffer_epochs` epochs stay in
    memory, plus the identifier sets that admission needs (record, transaction
    and committed ids; small strings). Nothing in a simulation step reads ledger
    history, so the step is unchanged.

    `tip()` describes the ledger at a completed epoch boundary for a checkpoint;
    `resume(tip)` truncates the stream to that boundary and continues it.
    `verify_chain()` and `replay_state()` stream the whole file with bounded
    memory (one value per resource).
    """

    def __init__(self, config_fingerprint: str, path: str, *, buffer_epochs: int = 8):
        super().__init__(config_fingerprint)
        from collections import deque
        self.path = str(path)
        self.buffer_epochs = max(1, int(buffer_epochs))
        self._buffer: "deque[tuple[EpochEvidenceBlock, tuple[LedgerRecord, ...]]]" = deque(maxlen=self.buffer_epochs)
        self._epoch_count = 0
        self._offset = 0
        self._writer_offsets: dict[str, int] = {}
        self._last_member_offset: int | None = None
        self._handle = None

    # -- storage ---------------------------------------------------------------
    def _append_member(self, obj: Any) -> int:
        import gzip
        start = self._offset
        data = gzip.compress((canonical_json(obj) + "\n").encode("utf-8"), compresslevel=6, mtime=0)
        if self._handle is None:
            self._handle = open(self.path, "ab")
        self._handle.write(data)
        self._handle.flush()
        self._offset += len(data)
        return start

    def _start_stream(self) -> None:
        if self._handle is None and self._offset == 0:
            open(self.path, "wb").close()
            self._append_member({"genesis": self._genesis, "config_fingerprint": self.config_fingerprint})

    def close(self) -> None:
        if self._handle is not None:
            import os
            self._handle.flush()
            os.fsync(self._handle.fileno())
            self._handle.close()
            self._handle = None

    # -- the ledger interface ----------------------------------------------------
    @property
    def records(self) -> tuple[LedgerRecord, ...]:
        """The buffered (most recent) records only; the rest are on disk."""
        return tuple(r for _, recs in self._buffer for r in recs)

    @property
    def epoch_blocks(self) -> tuple[EpochEvidenceBlock, ...]:
        return tuple(b for b, _ in self._buffer)

    @property
    def expected_epoch(self) -> int:
        return self._epoch_count

    def digest(self) -> str:
        return self._buffer[-1][0].epoch_digest if self._buffer else self._genesis_digest()

    def prepare_batch(self, entries, *, epoch=None):
        # The base implementation reads only the last block; give it the tail.
        self._blocks = [self._buffer[-1][0]] if self._buffer else []
        try:
            return super().prepare_batch(entries, epoch=epoch)
        finally:
            self._blocks = []

    def validate_epoch(self, epoch: int) -> None:
        if epoch != self._epoch_count:
            raise ProvenanceError(f"epoch {epoch} is not admissible; expected {self._epoch_count}")

    def commit_prepared_batch(self, prepared: PreparedLedgerBatch) -> tuple[LedgerRecord, ...]:
        self._start_stream()
        start = self._append_member({
            "epoch": prepared.epoch,
            "block": prepared.block.canonical(),
            "records": [r.canonical() for r in prepared.records],
        })
        self._buffer.append((prepared.block, prepared.records))
        self._last_member_offset = start
        self._epoch_count += 1
        for rec in prepared.records:
            self._record_ids.add(rec.record_id)
            self._transaction_ids.add(rec.transaction_id)
            if rec.status == "COMMITTED":
                self._committed_ids.update((rec.record_id, rec.transaction_id))
                for change in rec.committed:
                    self._writer_offsets[change.ref.as_key()] = start
        return prepared.records

    # -- reading the stream ---------------------------------------------------------
    def _members(self):
        """Stream every member from disk (the file always ends at the last
        committed epoch: writes are flushed per epoch and resume truncates)."""
        import gzip, json
        if self._handle is not None:
            self._handle.flush()
        with gzip.open(self.path, "rb") as stream:
            for line in stream:
                yield json.loads(line)

    def _member_at(self, offset: int) -> dict[str, Any]:
        import gzip, json, zlib
        with open(self.path, "rb") as raw:
            raw.seek(offset)
            d = zlib.decompressobj(16 + zlib.MAX_WBITS)
            out = b""
            while not d.eof:
                chunk = raw.read(1 << 20)
                if not chunk:
                    break
                out += d.decompress(chunk)
        return json.loads(out)

    def verify_chain(self) -> bool:
        """Stream the whole file and check it exactly as ReplayLedger does."""
        try:
            members = self._members()
            head = next(members)
            if digest_obj({"genesis": head["genesis"], "config": head["config_fingerprint"]}) != self._genesis_digest():
                return False
            previous = self._genesis_digest()
            committed_before: set[str] = set()
            seen_ids: set[str] = set()
            seen_tx: set[str] = set()
            count = 0
            for member in members:
                block = _block_from_canonical(member["block"])
                if block.epoch != count or block.previous_epoch_digest != previous:
                    return False
                recs = [_record_from_canonical(r) for r in member["records"]]
                for rec in recs:
                    if rec.record_id in seen_ids or rec.transaction_id in seen_tx:
                        return False
                    if rec.config_fingerprint != self.config_fingerprint or rec.epoch != block.epoch:
                        return False
                    if rec.record_id != f"E{rec.epoch:012d}:" + canonical_json([rec.transaction_id, rec.proposal_id]):
                        return False
                    if rec.previous_epoch_digest != previous:
                        return False
                    if digest_obj(rec.canonical_without_digest()) != rec.record_digest:
                        return False
                    if rec.status == "COMMITTED" and any(p not in committed_before for p in rec.causal_parents):
                        return False
                    seen_ids.add(rec.record_id)
                    seen_tx.add(rec.transaction_id)
                if tuple(sorted(r.record_digest for r in recs)) != block.record_digests:
                    return False
                if digest_obj(block.canonical_without_digest()) != block.epoch_digest:
                    return False
                for rec in recs:
                    if rec.status == "COMMITTED":
                        committed_before.update((rec.record_id, rec.transaction_id))
                previous = block.epoch_digest
                count += 1
            return count == self._epoch_count and previous == self.digest()
        except (OSError, ValueError, KeyError, StopIteration):
            return False

    def replay_state(self) -> dict[str, dict[str, dict[str, Any]]]:
        state: dict[str, dict[str, dict[str, Any]]] = {
            aid: {rid: {"value": copy.deepcopy(v), "version": 0} for rid, v in values.items()}
            for aid, values in self._genesis.items()
        }
        members = self._members()
        next(members)
        for member in members:
            for raw in sorted(member["records"], key=lambda r: (r["proposal_id"], r["transaction_id"])):
                if raw["status"] != "COMMITTED":
                    continue
                for change in raw["committed"]:
                    bucket = state.setdefault(change["authority_id"], {})
                    current = bucket.get(change["resource_id"])
                    if current is None:
                        raise ProvenanceError(f"replay unknown resource {change['authority_id']}:{change['resource_id']}")
                    if current["version"] != int(change["before_version"]):
                        raise ProvenanceError(f"replay version discontinuity {change['authority_id']}:{change['resource_id']}")
                    bucket[change["resource_id"]] = {"value": change["new_value"], "version": int(change["after_version"])}
        return state

    def latest_state(self) -> dict[str, dict[str, dict[str, Any]]]:
        """The current value of every resource, read from the epoch that last
        wrote it (a handful of members), checked against that epoch's digests."""
        state: dict[str, dict[str, dict[str, Any]]] = {
            aid: {rid: {"value": copy.deepcopy(v), "version": 0} for rid, v in values.items()}
            for aid, values in self._genesis.items()
        }
        members: dict[int, dict[str, Any]] = {}
        for offset in sorted(set(self._writer_offsets.values())):
            member = self._member_at(offset)
            block = _block_from_canonical(member["block"])
            recs = [_record_from_canonical(r) for r in member["records"]]
            if any(digest_obj(r.canonical_without_digest()) != r.record_digest for r in recs):
                raise ProvenanceError(f"record digest mismatch in epoch {block.epoch}")
            if tuple(sorted(r.record_digest for r in recs)) != block.record_digests:
                raise ProvenanceError(f"block digest mismatch in epoch {block.epoch}")
            if digest_obj(block.canonical_without_digest()) != block.epoch_digest:
                raise ProvenanceError(f"epoch digest mismatch in epoch {block.epoch}")
            members[offset] = member
        for key, offset in self._writer_offsets.items():
            for raw in sorted(members[offset]["records"], key=lambda r: (r["proposal_id"], r["transaction_id"])):
                if raw["status"] != "COMMITTED":
                    continue
                for change in raw["committed"]:
                    if f"{change['authority_id']}:{change['resource_id']}" == key:
                        state.setdefault(change["authority_id"], {})[change["resource_id"]] = {
                            "value": change["new_value"], "version": int(change["after_version"])}
        return state

    def fallible_projection(self) -> tuple[dict[str, Any], ...]:
        out = []
        members = self._members()
        next(members)
        for member in members:
            for raw in member["records"]:
                if raw["fallible_claims"]:
                    out.append({"epoch": raw["epoch"], "claim_source": raw["proposal_id"], "claims": raw["fallible_claims"]})
        return tuple(out)

    def export(self) -> dict[str, Any]:
        raise NotImplementedError("a streaming ledger is checkpointed by tip(), not exported in full")

    # -- checkpoint and resume ------------------------------------------------------
    def tip(self) -> dict[str, Any]:
        """The ledger at a completed epoch boundary (for a checkpoint)."""
        self.close()
        return {
            "kind": "streaming-v1",
            "path": self.path,
            "offset": self._offset,
            "config_fingerprint": self.config_fingerprint,
            "epoch_count": self._epoch_count,
            "digest": self.digest(),
            "last_block": self._buffer[-1][0].canonical() if self._buffer else None,
            "last_member_offset": self._last_member_offset,
            "buffer_epochs": self.buffer_epochs,
            "writer_offsets": dict(sorted(self._writer_offsets.items())),
            "record_ids": sorted(self._record_ids),
            "transaction_ids": sorted(self._transaction_ids),
            "committed_ids": sorted(self._committed_ids),
        }

    @classmethod
    def resume(cls, tip: dict[str, Any], path: str | None = None) -> "StreamingReplayLedger":
        """Continue the stream from a checkpoint's tip. Epochs written after
        the checkpoint are discarded (the file is truncated to the tip)."""
        import os
        if tip.get("kind") != "streaming-v1":
            raise ProvenanceError("not a streaming ledger tip")
        ledger = cls(str(tip["config_fingerprint"]), path or str(tip["path"]), buffer_epochs=int(tip["buffer_epochs"]))
        if os.path.getsize(ledger.path) < int(tip["offset"]):
            raise ProvenanceError("ledger stream is shorter than the checkpoint tip")
        with open(ledger.path, "r+b") as raw:
            raw.truncate(int(tip["offset"]))
        ledger._offset = int(tip["offset"])
        head = next(ledger._members())
        if head.get("config_fingerprint") != ledger.config_fingerprint:
            raise ProvenanceError("ledger stream config fingerprint mismatch")
        ledger._genesis = dict(head["genesis"])
        ledger._epoch_count = int(tip["epoch_count"])
        ledger._writer_offsets = {str(k): int(v) for k, v in tip["writer_offsets"].items()}
        ledger._record_ids = set(tip["record_ids"])
        ledger._transaction_ids = set(tip["transaction_ids"])
        ledger._committed_ids = set(tip["committed_ids"])
        if tip["last_block"] is not None:
            block = _block_from_canonical(tip["last_block"])
            ledger._last_member_offset = int(tip["last_member_offset"])
            last = ledger._member_at(ledger._last_member_offset)
            if last is None or last["block"] != tip["last_block"] or block.epoch_digest != tip["digest"]:
                raise ProvenanceError("ledger stream tail does not match the checkpoint tip")
            if digest_obj(block.canonical_without_digest()) != block.epoch_digest:
                raise ProvenanceError("checkpoint tip block digest mismatch")
            ledger._buffer.append((block, tuple(_record_from_canonical(r) for r in last["records"])))
        if ledger.digest() != tip["digest"]:
            raise ProvenanceError("ledger digest does not match the checkpoint tip")
        return ledger
