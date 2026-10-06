from __future__ import annotations

from pathlib import Path
import tempfile

from hrm_genesis import GenesisConfig, GenesisSimulation


def state(sim: GenesisSimulation):
    snap = sim.snapshot()
    return {
        "epoch": snap.epoch,
        "ledger_digest": snap.ledger_digest,
        "authorities": snap.authorities,
    }


def main() -> int:
    config = GenesisConfig(master_seed="genesis-g0-gate", physical_world_enabled=False, matter_enabled=False)

    direct = GenesisSimulation(config)
    direct.run(64)

    split = GenesisSimulation(config)
    split.run(23)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "genesis-g0.json"
        split.write_checkpoint(path)
        resumed = GenesisSimulation.load_checkpoint(path, config)
        resumed.run(41)

    checks = {
        "deterministic_replay": state(direct) == state(resumed),
        "ledger_valid_direct": direct.ledger.verify_chain(),
        "ledger_valid_resumed": resumed.ledger.verify_chain(),
        "expected_epoch": resumed.snapshot().epoch == 64,
        "expected_tick": resumed.snapshot().authorities["genesis.system"]["tick"]["value"] == 64,
    }

    failed = [name for name, passed in checks.items() if not passed]
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if failed:
        print("G0_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G0_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
