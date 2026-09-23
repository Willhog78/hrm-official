from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .authority import StateAuthority
from .fabric import TransactionFabric
from .ledger import ReplayLedger


def write_checkpoint(path: str | Path, orchestrator_state: dict[str, Any], fabric: TransactionFabric, ledger: ReplayLedger) -> None:
    payload = {
        "orchestrator": orchestrator_state,
        "fabric": fabric.checkpoint(),
        "ledger": ledger.export(),
    }
    Path(path).write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def load_checkpoint(path: str | Path) -> tuple[dict[str, Any], TransactionFabric, ReplayLedger, list[StateAuthority]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    ledger = ReplayLedger.from_export(payload["ledger"])
    authorities = [StateAuthority.from_checkpoint(p) for p in payload["fabric"]["authorities"]]
    fabric = TransactionFabric(
        payload["fabric"]["run_seed"],
        [a.port() for a in authorities],
        ledger,
        max_parallel_domains=int(payload["fabric"].get("max_parallel_domains", 32)),
    )
    return payload["orchestrator"], fabric, ledger, authorities
