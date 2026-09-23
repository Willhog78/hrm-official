from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from threading import Lock
import copy
import time

from .model import JSONValue, Mutation, ResourceRef, CommittedMutation


class AuthorityError(RuntimeError):
    pass


class StaleReadError(AuthorityError):
    pass


class OwnershipError(AuthorityError):
    pass


class PrepareError(AuthorityError):
    pass


class CommitStageError(AuthorityError):
    pass


@dataclass(frozen=True)
class SnapshotValue:
    value: JSONValue
    version: int


@dataclass(frozen=True)
class PreparedWrite:
    transaction_id: str
    mutations: tuple[CommittedMutation, ...]


class StateAuthority:
    """Synthetic state owner used to qualify Stage-1 coordination boundaries.

    Canonical state remains authority-private. Coordination receives only a narrow
    closure-backed port. This is deliberately generic and contains no Matter,
    climate, ecology, cognition, or social semantics.
    """

    def __init__(self, authority_id: str, initial: dict[str, JSONValue]):
        if not authority_id:
            raise ValueError("authority_id required")
        self.authority_id = authority_id
        self.__state: dict[str, JSONValue] = copy.deepcopy(initial)
        self.__versions: dict[str, int] = {key: 0 for key in initial}
        self.__prepared: dict[str, PreparedWrite] = {}
        self.__staged: dict[str, PreparedWrite] = {}
        self.__inject_prepare_failure: set[str] = set()
        self.__inject_stage_failure: set[str] = set()
        self.__materialize_delay_once: dict[str, float] = {}
        # Protects transaction bookkeeping maps only. Causal resource visibility is
        # protected by resource-scoped locks in TransactionFabric, not this lock.
        self.__bookkeeping_lock = Lock()

    def inject_prepare_failure_once(self, transaction_id: str) -> None:
        with self.__bookkeeping_lock:
            self.__inject_prepare_failure.add(transaction_id)

    def inject_stage_failure_once(self, transaction_id: str) -> None:
        with self.__bookkeeping_lock:
            self.__inject_stage_failure.add(transaction_id)

    def inject_materialize_delay_once(self, transaction_id: str, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("seconds must be >= 0")
        with self.__bookkeeping_lock:
            self.__materialize_delay_once[transaction_id] = float(seconds)

    def _snapshot(self, resource_ids: Iterable[str] | None = None) -> dict[str, SnapshotValue]:
        keys = sorted(self.__state) if resource_ids is None else sorted(set(resource_ids))
        out: dict[str, SnapshotValue] = {}
        for key in keys:
            if key not in self.__state:
                raise KeyError(key)
            out[key] = SnapshotValue(copy.deepcopy(self.__state[key]), self.__versions[key])
        return out

    def _prepare(self, transaction_id: str, mutations: tuple[Mutation, ...]) -> PreparedWrite:
        with self.__bookkeeping_lock:
            if transaction_id in self.__inject_prepare_failure:
                self.__inject_prepare_failure.remove(transaction_id)
                raise PrepareError(f"injected prepare failure: {transaction_id}")
            if transaction_id in self.__prepared or transaction_id in self.__staged:
                raise PrepareError(f"duplicate transaction {transaction_id}")

        seen: set[str] = set()
        committed: list[CommittedMutation] = []
        for mutation in sorted(mutations, key=lambda m: m.ref.resource_id):
            if mutation.ref.authority_id != self.authority_id:
                raise OwnershipError(f"{self.authority_id} cannot own {mutation.ref.as_key()}")
            rid = mutation.ref.resource_id
            if rid in seen:
                raise PrepareError(f"duplicate resource mutation {rid}")
            seen.add(rid)
            if rid not in self.__state:
                raise PrepareError(f"unknown resource {rid}")
            current = self.__versions[rid]
            if current != mutation.expected_version:
                raise StaleReadError(f"stale {rid}: expected {mutation.expected_version}, current {current}")
            committed.append(
                CommittedMutation(
                    ref=mutation.ref,
                    before_version=current,
                    after_version=current + 1,
                    new_value=copy.deepcopy(mutation.new_value),
                )
            )
        token = PreparedWrite(transaction_id, tuple(committed))
        with self.__bookkeeping_lock:
            self.__prepared[transaction_id] = token
        return token

    def _stage_commit(self, transaction_id: str) -> PreparedWrite:
        with self.__bookkeeping_lock:
            token = self.__prepared.get(transaction_id)
            if token is None:
                raise CommitStageError(f"transaction not prepared: {transaction_id}")
            if transaction_id in self.__inject_stage_failure:
                self.__inject_stage_failure.remove(transaction_id)
                raise CommitStageError(f"injected stage failure: {transaction_id}")
            self.__staged[transaction_id] = token
            del self.__prepared[transaction_id]
            return token

    def _abort(self, transaction_id: str) -> None:
        with self.__bookkeeping_lock:
            self.__prepared.pop(transaction_id, None)
            self.__staged.pop(transaction_id, None)
            self.__materialize_delay_once.pop(transaction_id, None)

    def _materialize_published(self, transaction_id: str) -> tuple[CommittedMutation, ...]:
        """Infallible after staging under the Stage-1 model.

        Every possible rejection/fault is required to happen before the publish
        barrier. A synthetic delay hook exists only to widen the observation window
        in atomic-visibility tests; it does not introduce a post-publish failure.
        """
        with self.__bookkeeping_lock:
            token = self.__staged.pop(transaction_id)
            delay = self.__materialize_delay_once.pop(transaction_id, 0.0)
        if delay:
            time.sleep(delay)
        for change in token.mutations:
            rid = change.ref.resource_id
            self.__state[rid] = copy.deepcopy(change.new_value)
            self.__versions[rid] = change.after_version
        return token.mutations

    def _checkpoint(self) -> dict[str, Any]:
        with self.__bookkeeping_lock:
            if self.__prepared or self.__staged:
                raise AuthorityError("checkpoint requires a clean transaction boundary")
        return {
            "authority_id": self.authority_id,
            "state": copy.deepcopy(self.__state),
            "versions": dict(self.__versions),
        }

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "StateAuthority":
        obj = cls(str(payload["authority_id"]), dict(payload["state"]))
        obj.__versions = {str(k): int(v) for k, v in dict(payload["versions"]).items()}
        return obj

    def port(self) -> "AuthorityPort":
        # SECURITY NOTE (post-Round-2 correction): a prior version of this port
        # closed over `self` (the whole StateAuthority instance) in every method.
        # That is a data-minimization defect, not just a naming defect: standard,
        # unprivileged Python reflection (`bound_method.__func__.__closure__`)
        # can retrieve the closed-over object and, from there, every private
        # attribute on it in one hop -- including transaction bookkeeping and
        # test-only failure-injection state that a legal caller has no business
        # reaching. Binding each capability to only the specific container(s) it
        # needs does not make private state literally unreachable from arbitrary
        # Python code in this process (CPython has no true in-process capability
        # boundary; `gc.get_referrers` can still walk to any live object). What
        # it does do is remove the one-hop "get the whole private object" path
        # and keep each capability's blast radius limited to the state it is
        # declared to operate on, which is the boundary Stage 1 can actually
        # promise. Hostile-process isolation, if ever required against genuinely
        # untrusted kernel code, needs an OS/interpreter process boundary and is
        # explicitly out of Stage-1 scope (see the Stage-10/distributed watch
        # item in the active contract).
        authority_id = self.authority_id
        state = self.__state
        versions = self.__versions
        prepared = self.__prepared
        staged = self.__staged
        bookkeeping_lock = self.__bookkeeping_lock
        inject_prepare_failure = self.__inject_prepare_failure
        inject_stage_failure = self.__inject_stage_failure
        materialize_delay_once = self.__materialize_delay_once

        def _port_snapshot(resource_ids: Iterable[str] | None = None) -> dict[str, SnapshotValue]:
            keys = sorted(state) if resource_ids is None else sorted(set(resource_ids))
            out: dict[str, SnapshotValue] = {}
            for key in keys:
                if key not in state:
                    raise KeyError(key)
                out[key] = SnapshotValue(copy.deepcopy(state[key]), versions[key])
            return out

        def _port_prepare(transaction_id: str, mutations: tuple[Mutation, ...]) -> PreparedWrite:
            with bookkeeping_lock:
                if transaction_id in inject_prepare_failure:
                    inject_prepare_failure.remove(transaction_id)
                    raise PrepareError(f"injected prepare failure: {transaction_id}")
                if transaction_id in prepared or transaction_id in staged:
                    raise PrepareError(f"duplicate transaction {transaction_id}")

            seen: set[str] = set()
            committed: list[CommittedMutation] = []
            for mutation in sorted(mutations, key=lambda m: m.ref.resource_id):
                if mutation.ref.authority_id != authority_id:
                    raise OwnershipError(f"{authority_id} cannot own {mutation.ref.as_key()}")
                rid = mutation.ref.resource_id
                if rid in seen:
                    raise PrepareError(f"duplicate resource mutation {rid}")
                seen.add(rid)
                if rid not in state:
                    raise PrepareError(f"unknown resource {rid}")
                current = versions[rid]
                if current != mutation.expected_version:
                    raise StaleReadError(f"stale {rid}: expected {mutation.expected_version}, current {current}")
                committed.append(
                    CommittedMutation(
                        ref=mutation.ref,
                        before_version=current,
                        after_version=current + 1,
                        new_value=copy.deepcopy(mutation.new_value),
                    )
                )
            token = PreparedWrite(transaction_id, tuple(committed))
            with bookkeeping_lock:
                prepared[transaction_id] = token
            return token

        def _port_stage_commit(transaction_id: str) -> PreparedWrite:
            with bookkeeping_lock:
                token = prepared.get(transaction_id)
                if token is None:
                    raise CommitStageError(f"transaction not prepared: {transaction_id}")
                if transaction_id in inject_stage_failure:
                    inject_stage_failure.remove(transaction_id)
                    raise CommitStageError(f"injected stage failure: {transaction_id}")
                staged[transaction_id] = token
                del prepared[transaction_id]
                return token

        def _port_abort(transaction_id: str) -> None:
            with bookkeeping_lock:
                prepared.pop(transaction_id, None)
                staged.pop(transaction_id, None)
                materialize_delay_once.pop(transaction_id, None)

        def _port_materialize_published(transaction_id: str) -> tuple[CommittedMutation, ...]:
            with bookkeeping_lock:
                token = staged.pop(transaction_id)
                delay = materialize_delay_once.pop(transaction_id, 0.0)
            if delay:
                time.sleep(delay)
            for change in token.mutations:
                rid = change.ref.resource_id
                state[rid] = copy.deepcopy(change.new_value)
                versions[rid] = change.after_version
            return token.mutations

        def _port_checkpoint() -> dict[str, Any]:
            with bookkeeping_lock:
                if prepared or staged:
                    raise AuthorityError("checkpoint requires a clean transaction boundary")
            return {
                "authority_id": authority_id,
                "state": copy.deepcopy(state),
                "versions": dict(versions),
            }

        class _ClosurePort(AuthorityPort):
            __slots__ = ()

            @property
            def authority_id(self) -> str:
                return authority_id

            def snapshot(self, resource_ids: Iterable[str] | None = None) -> dict[str, SnapshotValue]:
                return _port_snapshot(resource_ids)

            def prepare(self, transaction_id: str, mutations: tuple[Mutation, ...]) -> PreparedWrite:
                return _port_prepare(transaction_id, mutations)

            def stage_commit(self, transaction_id: str) -> PreparedWrite:
                return _port_stage_commit(transaction_id)

            def abort(self, transaction_id: str) -> None:
                _port_abort(transaction_id)

            def materialize_published(self, transaction_id: str) -> tuple[CommittedMutation, ...]:
                return _port_materialize_published(transaction_id)

            def checkpoint(self) -> dict[str, Any]:
                return _port_checkpoint()

        return _ClosurePort()


class AuthorityPort:
    """Declared legal interface visible to coordination code."""

    @property
    def authority_id(self) -> str:  # pragma: no cover - interface only
        raise NotImplementedError

    def snapshot(self, resource_ids: Iterable[str] | None = None) -> dict[str, SnapshotValue]:  # pragma: no cover
        raise NotImplementedError

    def prepare(self, transaction_id: str, mutations: tuple[Mutation, ...]) -> PreparedWrite:  # pragma: no cover
        raise NotImplementedError

    def stage_commit(self, transaction_id: str) -> PreparedWrite:  # pragma: no cover
        raise NotImplementedError

    def abort(self, transaction_id: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def materialize_published(self, transaction_id: str) -> tuple[CommittedMutation, ...]:  # pragma: no cover
        raise NotImplementedError

    def checkpoint(self) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError
