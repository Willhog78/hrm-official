from __future__ import annotations

from threading import Lock
from typing import Any
import hashlib
import json

from .entities import MatterEntity
from .transform import split as _split, merge as _merge, add_energy as _add_energy, ConservationError


class BoundaryError(RuntimeError):
    pass


def _build_ops(entities: dict[str, MatterEntity], lock: Lock, id_box: list[int]):
    """Build the kernel's operations as closures over only these three local
    containers -- never over a `self`/kernel object. This is the Stage-1
    Round-2 external-review lesson applied from the start rather than bolted
    on afterward: `entities`, `lock`, and `id_box` are the entire reachable
    surface from any of these closures. A determined in-process caller can
    still reach `entities`/`lock` themselves through reflection -- CPython has
    no true in-process capability boundary -- but there is no single hop to a
    `MatterKernel` object carrying every other private attribute at once.
    """

    def fresh_id() -> str:
        with lock:
            id_box[0] += 1
            return f"M{id_box[0]:010d}"

    def register(entity: MatterEntity) -> str:
        entity_id = fresh_id()
        with lock:
            entities[entity_id] = entity
        return entity_id

    def get(entity_id: str) -> MatterEntity:
        with lock:
            entity = entities.get(entity_id)
        if entity is None:
            raise KeyError(entity_id)
        return entity

    def apply_split(entity_id: str, ratios: tuple[float, ...]) -> tuple[str, ...]:
        with lock:
            entity = entities.get(entity_id)
            if entity is None:
                raise KeyError(entity_id)
        parts = _split(entity, ratios)
        ids = tuple(fresh_id() for _ in parts)
        with lock:
            for pid, part in zip(ids, parts):
                entities[pid] = part
            del entities[entity_id]
        return ids

    def apply_merge(entity_ids: tuple[str, ...]) -> str:
        with lock:
            missing = [eid for eid in entity_ids if eid not in entities]
            if missing:
                raise KeyError(missing[0])
            parts = [entities[eid] for eid in entity_ids]
        result = _merge(parts)
        new_id = fresh_id()
        with lock:
            entities[new_id] = result
            for eid in entity_ids:
                del entities[eid]
        return new_id

    def apply_add_energy(entity_id: str, delta_j: float) -> str:
        with lock:
            entity = entities.get(entity_id)
            if entity is None:
                raise KeyError(entity_id)
        result = _add_energy(entity, delta_j)
        new_id = fresh_id()
        with lock:
            entities[new_id] = result
            del entities[entity_id]
        return new_id

    def state_digest() -> str:
        with lock:
            items = sorted(entities.items())
        payload = json.dumps({eid: e.canonical() for eid, e in items}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def checkpoint() -> dict[str, Any]:
        with lock:
            return {
                "next_id": id_box[0],
                "entities": {eid: e.canonical() for eid, e in sorted(entities.items())},
            }

    return {
        "register": register,
        "get": get,
        "apply_split": apply_split,
        "apply_merge": apply_merge,
        "apply_add_energy": apply_add_energy,
        "state_digest": state_digest,
        "checkpoint": checkpoint,
    }


class MatterPort:
    """Declared legal interface visible to later-stage kernels (M2.7).

    Notably absent: no `register`. Later-stage kernels may observe and
    transform existing matter but do not get to conjure new matter into
    existence outside the Matter kernel's own genesis -- that boundary is
    deliberate, not an oversight.
    """

    def get(self, entity_id: str) -> MatterEntity:  # pragma: no cover - interface only
        raise NotImplementedError

    def split(self, entity_id: str, ratios: tuple[float, ...]) -> tuple[str, ...]:  # pragma: no cover
        raise NotImplementedError

    def merge(self, entity_ids: tuple[str, ...]) -> str:  # pragma: no cover
        raise NotImplementedError

    def add_energy(self, entity_id: str, delta_j: float) -> str:  # pragma: no cover
        raise NotImplementedError

    def state_digest(self) -> str:  # pragma: no cover
        raise NotImplementedError


class MatterKernel:
    """Owns all Matter entities for one kernel instance.

    Entities are only ever created, split, merged, or re-energized through the
    kernel's declared operations (M2.7). `MatterEntity` itself is an immutable
    dataclass, so even a caller holding a reference to one cannot mutate it in
    place -- the only way to change matter state is to call back into the
    kernel and receive a new entity id.
    """

    def __init__(self, _initial_entities: dict[str, MatterEntity] | None = None, _initial_next_id: int = 0):
        entities: dict[str, MatterEntity] = dict(_initial_entities or {})
        lock = Lock()
        id_box = [int(_initial_next_id)]
        ops = _build_ops(entities, lock, id_box)
        # Every public operation is a plain closure assigned as an instance
        # attribute, not a `def method(self, ...)` -- so accessing
        # `kernel.register` returns the closure object itself rather than a
        # bound method, and no port operation's closure chain contains a
        # `MatterKernel` instance to walk back to.
        self.register = ops["register"]
        self.get = ops["get"]
        self.apply_split = ops["apply_split"]
        self.apply_merge = ops["apply_merge"]
        self.apply_add_energy = ops["apply_add_energy"]
        self.state_digest = ops["state_digest"]
        self.checkpoint = ops["checkpoint"]

    @classmethod
    def from_checkpoint(cls, payload: dict[str, Any]) -> "MatterKernel":
        entities = {eid: MatterEntity(**raw) for eid, raw in payload["entities"].items()}
        return cls(_initial_entities=entities, _initial_next_id=int(payload["next_id"]))

    def port(self) -> "MatterPort":
        register = self.register
        get = self.get
        apply_split = self.apply_split
        apply_merge = self.apply_merge
        apply_add_energy = self.apply_add_energy
        state_digest = self.state_digest

        class _MatterPort(MatterPort):
            __slots__ = ()

            def get(self, entity_id: str) -> MatterEntity:
                return get(entity_id)

            def split(self, entity_id: str, ratios: tuple[float, ...]) -> tuple[str, ...]:
                return apply_split(entity_id, ratios)

            def merge(self, entity_ids: tuple[str, ...]) -> str:
                return apply_merge(entity_ids)

            def add_energy(self, entity_id: str, delta_j: float) -> str:
                return apply_add_energy(entity_id, delta_j)

            def state_digest(self) -> str:
                return state_digest()

        return _MatterPort()
