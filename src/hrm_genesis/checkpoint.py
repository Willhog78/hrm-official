from __future__ import annotations

from pathlib import Path

from hrm_coordination import load_checkpoint, write_checkpoint

from .config import GenesisConfig


def write_genesis_checkpoint(path: str | Path, simulation: "GenesisSimulation") -> None:
    write_checkpoint(
        path,
        simulation.orchestrator.checkpoint(),
        simulation.fabric,
        simulation.ledger,
    )


def load_genesis_checkpoint(path: str | Path, config: GenesisConfig) -> "GenesisSimulation":
    from .runner import GenesisSimulation

    orchestrator_state, fabric, ledger, authorities = load_checkpoint(path)
    if ledger.config_fingerprint != config.fingerprint():
        raise ValueError("checkpoint config fingerprint does not match GenesisConfig")
    return GenesisSimulation._from_restored(
        config=config,
        orchestrator_state=orchestrator_state,
        fabric=fabric,
        ledger=ledger,
        authorities=authorities,
    )
