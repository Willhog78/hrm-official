from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hrm_coordination.fabric import TransactionFabric


@dataclass(frozen=True)
class GenesisSnapshot:
    epoch: int
    ledger_digest: str
    authorities: dict[str, dict[str, dict[str, Any]]]


def capture_snapshot(
    *,
    epoch: int,
    ledger_digest: str,
    fabric: TransactionFabric,
) -> GenesisSnapshot:
    authorities: dict[str, dict[str, dict[str, Any]]] = {}
    for authority_id in fabric.authority_ids:
        authorities[authority_id] = {
            resource_id: {"value": value.value, "version": value.version}
            for resource_id, value in fabric.projection(authority_id).items()
        }
    return GenesisSnapshot(
        epoch=epoch,
        ledger_digest=ledger_digest,
        authorities=authorities,
    )
