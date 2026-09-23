from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .authority import StateAuthority
from .fabric import TransactionFabric
from .ledger import ProvenanceError, ReplayLedger


def write_checkpoint(path: str | Path, orchestrator_state: dict[str, Any], fabric: TransactionFabric, ledger: ReplayLedger) -> None:
    payload = {
        "orchestrator": orchestrator_state,
        "fabric": fabric.checkpoint(),
        "ledger": ledger.export(),
    }
    Path(path).write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")


def _verify_state_matches_ledger(authority_payloads: list[dict[str, Any]], ledger: ReplayLedger) -> None:
    """Reject a checkpoint whose authority state is not what the verified ledger replays to.

    The ledger is hash-chained; authority state is not. Without this check an edited
    state value would load silently and diverge from replay evidence.
    """
    replayed = ledger.replay_state()
    stored: dict[str, dict[str, dict[str, Any]]] = {}
    for raw in authority_payloads:
        state = dict(raw["state"])
        versions = {str(k): int(v) for k, v in dict(raw["versions"]).items()}
        if set(versions) != set(state):
            raise ProvenanceError(f"checkpoint authority {raw['authority_id']} has mismatched state/version keys")
        stored[str(raw["authority_id"])] = {
            rid: {"value": value, "version": versions[rid]} for rid, value in state.items()
        }
    if stored != replayed:
        diverged = sorted(set(stored) ^ set(replayed) | {
            aid for aid in set(stored) & set(replayed) if stored[aid] != replayed[aid]
        })
        raise ProvenanceError(f"checkpoint authority state does not match ledger replay: {diverged}")


def load_checkpoint(path: str | Path) -> tuple[dict[str, Any], TransactionFabric, ReplayLedger, list[StateAuthority]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    ledger = ReplayLedger.from_export(payload["ledger"])
    _verify_state_matches_ledger(payload["fabric"]["authorities"], ledger)
    authorities = [StateAuthority.from_checkpoint(p) for p in payload["fabric"]["authorities"]]
    fabric = TransactionFabric(
        payload["fabric"]["run_seed"],
        [a.port() for a in authorities],
        ledger,
        max_parallel_domains=int(payload["fabric"].get("max_parallel_domains", 32)),
    )
    return payload["orchestrator"], fabric, ledger, authorities
