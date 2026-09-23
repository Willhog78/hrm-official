from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from threading import Lock, RLock
from typing import Iterable, Sequence
import hashlib

from .authority import AuthorityPort, AuthorityError
from .ledger import ReplayLedger, ProvenanceError
from .model import (
    CommittedMutation,
    ProposalResult,
    ResolutionBatch,
    TransactionProposal,
    canonical_json,
    digest_obj,
)


@dataclass(frozen=True)
class PublishDecision:
    transaction_id: str
    participant_ids: tuple[str, ...]
    epoch: int
    decision_digest: str


@dataclass(frozen=True)
class ConflictDomainPlan:
    domain_id: str
    proposal_ids: tuple[str, ...]
    resource_keys: tuple[str, ...]


class TransactionFabric:
    """Deterministic, resource-scoped arbitration and atomic transaction fabric.

    Independent conflict domains are discovered from resource overlap and are
    dispatched concurrently by default. Causal state never relies on thread race
    order: arbitration is completed deterministically before dispatch, each domain
    owns disjoint resource keys, and ledger evidence is merged canonically only
    after domain execution completes.

    Cross-authority transactions use resource-scoped publication locks. The locks
    are held across prepare -> stage -> publish -> materialize, and legal projection
    reads acquire the same locks. This closes the successful-publication observation
    window without introducing one universal state lock.
    """

    def __init__(
        self,
        run_seed: str,
        ports: Iterable[AuthorityPort],
        ledger: ReplayLedger,
        *,
        max_parallel_domains: int = 32,
    ):
        self.run_seed = str(run_seed)
        self.ledger = ledger
        port_list = list(ports)
        self._ports = {p.authority_id: p for p in port_list}
        if len(self._ports) == 0:
            raise ValueError("at least one authority required")
        if len(self._ports) != len(port_list):
            raise ValueError("duplicate authority_id")
        if int(max_parallel_domains) < 1:
            raise ValueError("max_parallel_domains must be >= 1")
        self.max_parallel_domains = int(max_parallel_domains)

        self._published: dict[str, PublishDecision] = {}
        self._published_lock = Lock()
        # One resolve call is one authoritative epoch-admission/finalization unit.
        # Independent conflict domains still execute concurrently *inside* the epoch.
        self._resolve_lock = Lock()

        # Static resource universe for the Stage-1 synthetic authority fixture.
        # Later kernel adapters may provide their own stable resource registry, but
        # resource locks remain scoped to causal ownership keys rather than global.
        self._authority_resources: dict[str, tuple[str, ...]] = {}
        self._resource_locks: dict[str, RLock] = {}
        for aid, port in sorted(self._ports.items()):
            rids = tuple(sorted(port.snapshot().keys()))
            self._authority_resources[aid] = rids
            for rid in rids:
                self._resource_locks[f"{aid}:{rid}"] = RLock()

    @property
    def authority_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._ports))

    def _keys_for_projection(self, authority_id: str, resource_ids: Iterable[str] | None) -> tuple[str, ...]:
        if authority_id not in self._ports:
            raise KeyError(authority_id)
        if resource_ids is None:
            rids = self._authority_resources[authority_id]
        else:
            rids = tuple(sorted(set(resource_ids)))
        keys = tuple(f"{authority_id}:{rid}" for rid in rids)
        missing = [key for key in keys if key not in self._resource_locks]
        if missing:
            raise KeyError(missing[0].split(":", 1)[1])
        return tuple(sorted(keys))

    def projection(self, authority_id: str, resource_ids: Iterable[str] | None = None):
        normalized = None if resource_ids is None else tuple(resource_ids)
        keys = self._keys_for_projection(authority_id, normalized)
        with ExitStack() as stack:
            for key in keys:
                stack.enter_context(self._resource_locks[key])
            return self._ports[authority_id].snapshot(normalized)

    def _proposal_rank(self, proposal: TransactionProposal) -> str:
        payload = {
            "seed": self.run_seed,
            "epoch": proposal.logical_epoch,
            "proposal_id": proposal.proposal_id,
            "transaction_id": proposal.transaction_id,
            "conflict_keys": proposal.conflict_keys(),
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    def _validate_shape(self, proposal: TransactionProposal) -> None:
        if not proposal.proposal_id or not proposal.transaction_id or not proposal.proposer_id:
            raise ValueError("proposal, transaction and proposer ids are required")
        if not proposal.mutations:
            raise ValueError("transaction must contain at least one mutation")
        if len({m.ref.as_key() for m in proposal.mutations}) != len(proposal.mutations):
            raise ValueError("duplicate mutation resource")
        missing = sorted({m.ref.authority_id for m in proposal.mutations} - set(self._ports))
        if missing:
            raise ValueError(f"unknown authority ids: {missing}")
        unknown_resources = sorted(
            m.ref.as_key() for m in proposal.mutations if m.ref.as_key() not in self._resource_locks
        )
        if unknown_resources:
            raise ValueError(f"unknown resource keys: {unknown_resources}")

    def _component_indexes(self, proposals: Sequence[TransactionProposal]) -> list[list[int]]:
        # Union-find over resource conflicts. A multi-authority transaction is one
        # proposal node and therefore naturally keeps all of its participants in
        # the same component without globally coupling unrelated work.
        n = len(proposals)
        parent = list(range(n))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                if ra < rb:
                    parent[rb] = ra
                else:
                    parent[ra] = rb

        owners: dict[str, int] = {}
        for i, proposal in enumerate(proposals):
            for key in proposal.conflict_keys():
                if key in owners:
                    union(i, owners[key])
                else:
                    owners[key] = i
        groups: dict[int, list[int]] = defaultdict(list)
        for i in range(n):
            groups[find(i)].append(i)
        components = list(groups.values())
        components.sort(key=lambda ids: min(proposals[i].proposal_id for i in ids))
        return components

    def plan_conflict_domains(self, proposals: Sequence[TransactionProposal]) -> tuple[ConflictDomainPlan, ...]:
        for p in proposals:
            self._validate_shape(p)
        plans = []
        for idx, comp in enumerate(self._component_indexes(proposals)):
            pids = tuple(sorted(proposals[i].proposal_id for i in comp))
            keys = tuple(sorted({key for i in comp for key in proposals[i].conflict_keys()}))
            plans.append(ConflictDomainPlan(domain_id=f"D{idx:08d}", proposal_ids=pids, resource_keys=keys))
        return tuple(plans)

    def _select_nonconflicting(self, proposals: Sequence[TransactionProposal]) -> tuple[list[TransactionProposal], dict[str, str]]:
        ordered = sorted(proposals, key=lambda p: (self._proposal_rank(p), p.proposal_id, p.transaction_id))
        occupied: set[str] = set()
        winners: list[TransactionProposal] = []
        rejected: dict[str, str] = {}
        for proposal in ordered:
            keys = set(proposal.conflict_keys())
            if keys & occupied:
                rejected[proposal.proposal_id] = "CONFLICT_LOST"
                continue
            occupied.update(keys)
            winners.append(proposal)
        return winners, rejected

    def _execute_transaction(self, epoch: int, proposal: TransactionProposal) -> tuple[ProposalResult, tuple[CommittedMutation, ...]]:
        """Prepare and stage one winning transaction without publishing causal state."""
        participants = tuple(sorted({m.ref.authority_id for m in proposal.mutations}))
        by_authority: dict[str, list] = defaultdict(list)
        for mutation in proposal.mutations:
            by_authority[mutation.ref.authority_id].append(mutation)

        keys = tuple(sorted(proposal.conflict_keys()))
        with ExitStack() as stack:
            for key in keys:
                stack.enter_context(self._resource_locks[key])
            try:
                for aid in participants:
                    self._ports[aid].prepare(proposal.transaction_id, tuple(by_authority[aid]))

                staged: list[CommittedMutation] = []
                for aid in participants:
                    token = self._ports[aid].stage_commit(proposal.transaction_id)
                    staged.extend(token.mutations)
                staged.sort(key=lambda m: m.ref.as_key())
                return ProposalResult(proposal.proposal_id, proposal.transaction_id, "COMMITTED"), tuple(staged)
            except (AuthorityError, ValueError) as exc:
                for aid in participants:
                    self._ports[aid].abort(proposal.transaction_id)
                return ProposalResult(
                    proposal.proposal_id,
                    proposal.transaction_id,
                    "REJECTED",
                    type(exc).__name__ + ": " + str(exc),
                ), ()

    def _abort_staged(self, proposal: TransactionProposal) -> None:
        for aid in sorted({m.ref.authority_id for m in proposal.mutations}):
            self._ports[aid].abort(proposal.transaction_id)
        with self._published_lock:
            self._published.pop(proposal.transaction_id, None)

    def _materialize_after_ledger_admission(
        self,
        epoch: int,
        proposals: Sequence[TransactionProposal],
        prepared_ledger,
    ) -> None:
        """Materialize staged winners behind resource-scoped visibility locks.

        Winning proposals are pairwise resource-disjoint after arbitration. The
        coordinator therefore acquires the union of their resource locks once,
        lets disjoint authority work materialize concurrently, finalizes the
        already-prevalidated ledger batch, and only then releases legal readers.
        """
        all_keys = tuple(sorted({key for proposal in proposals for key in proposal.conflict_keys()}))
        with ExitStack() as stack:
            for key in all_keys:
                stack.enter_context(self._resource_locks[key])

            def materialize(proposal: TransactionProposal) -> None:
                participants = tuple(sorted({m.ref.authority_id for m in proposal.mutations}))
                decision = PublishDecision(
                    transaction_id=proposal.transaction_id,
                    participant_ids=participants,
                    epoch=epoch,
                    decision_digest=digest_obj({
                        "transaction_id": proposal.transaction_id,
                        "participants": participants,
                        "epoch": epoch,
                        "proposal_digest": proposal.digest(),
                    }),
                )
                with self._published_lock:
                    self._published[proposal.transaction_id] = decision
                for aid in participants:
                    self._ports[aid].materialize_published(proposal.transaction_id)

            if proposals:
                workers = min(len(proposals), self.max_parallel_domains)
                if workers == 1:
                    for proposal in proposals:
                        materialize(proposal)
                else:
                    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="hrm-finalize") as pool:
                        futures = [pool.submit(materialize, proposal) for proposal in proposals]
                        for future in futures:
                            future.result()

            # No rejection-capable work remains here. Legal projections cannot
            # acquire any changed resource until this evidence is installed.
            self.ledger.commit_prepared_batch(prepared_ledger)

    def resolve(
        self,
        epoch: int,
        proposals: Sequence[TransactionProposal],
        component_execution_order: Sequence[int] | None = None,
    ) -> ResolutionBatch:
        with self._resolve_lock:
            # Epoch admissibility and historical transaction identity are checked
            # before any authority is allowed to prepare or stage state.
            self.ledger.validate_epoch(epoch)

            unique_ids = {p.proposal_id for p in proposals}
            if len(unique_ids) != len(proposals):
                raise ValueError("duplicate proposal_id in batch")
            tx_ids = {p.transaction_id for p in proposals}
            if len(tx_ids) != len(proposals):
                raise ValueError("duplicate transaction_id in batch")
            self.ledger.validate_transaction_ids(proposals)

            for proposal in proposals:
                self._validate_shape(proposal)
                if proposal.logical_epoch != epoch:
                    raise ValueError("proposal epoch mismatch")

            # Validate authoritative provenance against prior evidence. Invalid
            # provenance is a proposal rejection, not a whole-epoch admission error.
            valid: list[TransactionProposal] = []
            invalid_results: dict[str, ProposalResult] = {}
            for proposal in proposals:
                try:
                    self.ledger.validate_proposal(proposal)
                    valid.append(proposal)
                except ProvenanceError as exc:
                    invalid_results[proposal.proposal_id] = ProposalResult(
                        proposal.proposal_id,
                        proposal.transaction_id,
                        "REJECTED",
                        type(exc).__name__ + ": " + str(exc),
                    )

            components = self._component_indexes(valid)
            if component_execution_order is not None:
                execution = list(component_execution_order)
                if sorted(execution) != list(range(len(components))):
                    raise ValueError("component_execution_order must be a permutation of component indexes")
            else:
                execution = list(range(len(components)))

            winners_all: list[TransactionProposal] = []
            conflict_rejected: dict[str, str] = {}
            for comp in components:
                subset = [valid[i] for i in comp]
                winners, rejected = self._select_nonconflicting(subset)
                winners_all.extend(winners)
                conflict_rejected.update(rejected)

            arbitration_digest = digest_obj({
                "epoch": epoch,
                "proposal_digests": sorted(p.digest() for p in proposals),
                "winner_ids": sorted(p.proposal_id for p in winners_all),
                "invalid_ids": sorted(invalid_results),
                "rejected": sorted(conflict_rejected.items()),
                "domains": [
                    {
                        "proposals": sorted(valid[i].proposal_id for i in comp),
                        "keys": sorted({k for i in comp for k in valid[i].conflict_keys()}),
                    }
                    for comp in components
                ],
            })

            result_map: dict[str, ProposalResult] = dict(invalid_results)
            committed_by_pid: dict[str, tuple[CommittedMutation, ...]] = {}
            winner_by_pid = {p.proposal_id: p for p in winners_all}
            valid_by_pid = {p.proposal_id: p for p in valid}

            for pid, reason in conflict_rejected.items():
                proposal = valid_by_pid[pid]
                result_map[pid] = ProposalResult(proposal.proposal_id, proposal.transaction_id, "REJECTED", reason)
                committed_by_pid[pid] = ()

            def execute_component(comp_index: int):
                comp = components[comp_index]
                pids = {valid[i].proposal_id for i in comp}
                local: list[tuple[str, ProposalResult, tuple[CommittedMutation, ...]]] = []
                for proposal in sorted(
                    (winner_by_pid[pid] for pid in pids if pid in winner_by_pid),
                    key=lambda x: (x.transaction_id, x.proposal_id),
                ):
                    result, staged = self._execute_transaction(epoch, proposal)
                    local.append((proposal.proposal_id, result, staged))
                return local

            try:
                if component_execution_order is not None or len(execution) <= 1 or self.max_parallel_domains == 1:
                    component_results = [execute_component(i) for i in execution]
                else:
                    workers = min(len(execution), self.max_parallel_domains)
                    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="hrm-domain") as pool:
                        futures = [pool.submit(execute_component, i) for i in execution]
                        component_results = [future.result() for future in futures]
            except BaseException:
                # An unexpected failure in any domain must not leave other winners
                # prepared/staged: that would block checkpoints indefinitely. The
                # executor has joined every domain before this point; abort is
                # idempotent, so aborting every winner is safe.
                for proposal in winners_all:
                    self._abort_staged(proposal)
                raise

            for local in component_results:
                for pid, result, staged in local:
                    result_map[pid] = result
                    committed_by_pid[pid] = staged

            # Every proposal in the admitted batch, including provenance-rejected
            # ones, leaves evidence. This records its transaction_id so it cannot
            # be reused later in the run/replay domain.
            evidence_entries = [
                (p, result_map[p.proposal_id].status, arbitration_digest, committed_by_pid.get(p.proposal_id, ()))
                for p in sorted(proposals, key=lambda x: (x.proposal_id, x.transaction_id))
            ]

            # Critical Round-2 correction: every rejection-capable ledger operation
            # happens here, before any staged transaction becomes visible.
            try:
                prepared_ledger = self.ledger.prepare_batch(evidence_entries, epoch=epoch)
            except BaseException:
                for proposal in winners_all:
                    if result_map.get(proposal.proposal_id, ProposalResult("", "", "REJECTED")).status == "COMMITTED":
                        self._abort_staged(proposal)
                raise

            staged_winners = [
                proposal for proposal in winners_all
                if result_map[proposal.proposal_id].status == "COMMITTED"
            ]
            self._materialize_after_ledger_admission(epoch, staged_winners, prepared_ledger)

            ordered_results = tuple(result_map[p.proposal_id] for p in sorted(proposals, key=lambda x: x.proposal_id))
            committed_all = [
                mutation
                for pid, changes in committed_by_pid.items()
                if result_map[pid].status == "COMMITTED"
                for mutation in changes
            ]
            committed_all.sort(key=lambda m: (m.ref.as_key(), m.after_version))
            return ResolutionBatch(epoch, ordered_results, tuple(committed_all), arbitration_digest)

    def causal_state_digest(self) -> str:
        snapshot = {}
        for aid in sorted(self._ports):
            snap = self.projection(aid)
            snapshot[aid] = {rid: {"value": v.value, "version": v.version} for rid, v in sorted(snap.items())}
        return digest_obj(snapshot)

    def checkpoint(self) -> dict:
        # Checkpoint callers are expected to be at a completed transaction boundary.
        # Acquire all resource locks in canonical order anyway so a legal concurrent
        # projection/transaction cannot leak a torn snapshot.
        with ExitStack() as stack:
            for key in sorted(self._resource_locks):
                stack.enter_context(self._resource_locks[key])
            with self._published_lock:
                published = {
                    tid: {
                        "transaction_id": d.transaction_id,
                        "participant_ids": list(d.participant_ids),
                        "epoch": d.epoch,
                        "decision_digest": d.decision_digest,
                    }
                    for tid, d in sorted(self._published.items())
                }
            return {
                "run_seed": self.run_seed,
                "max_parallel_domains": self.max_parallel_domains,
                "authorities": [self._ports[aid].checkpoint() for aid in sorted(self._ports)],
                "published": published,
            }
