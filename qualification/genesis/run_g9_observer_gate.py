from __future__ import annotations

from hrm_coordination.model import digest_obj
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.observer import observe_genesis


def _causal_digest(sim: GenesisSimulation) -> str:
    return digest_obj(
        {
            "world": sim.world_state(),
            "matter": sim.matter_state(),
            "producers": sim.ecology_state(),
            "consumers": sim.consumer_state(),
            "humans": sim.human_state(),
            "ledger": sim.ledger.digest(),
            "epoch": sim.orchestrator.epoch,
        }
    )


def _observe(sim: GenesisSimulation) -> dict:
    before = _causal_digest(sim)
    report = observe_genesis(
        world_state=sim.world_state(),
        matter_state=sim.matter_state(),
        producer_state=sim.ecology_state(),
        consumer_state=sim.consumer_state(),
        human_state=sim.human_state(),
    )
    after = _causal_digest(sim)
    if before != after:
        raise AssertionError("observer mutated causal state")
    return report


def main() -> int:
    config = GenesisConfig(
        master_seed="genesis-g9-observer-isolation",
        world_width=8,
        world_height=8,
        ticks_per_year=12,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_cognition_enabled=True,
        human_actions_enabled=True,
        multi_population_enabled=True,
    )

    control = GenesisSimulation(config)
    observed = GenesisSimulation(config)

    reports = []
    for _ in range(36):
        control.run(1)
        observed.run(1)
        reports.append(_observe(observed))

    checks = {
        "observer_produces_reports": len(reports) == 36,
        "observer_has_environment_metrics": "environment" in reports[-1],
        "observer_has_ecology_metrics": "ecology" in reports[-1],
        "observer_has_population_metrics": "population" in reports[-1],
        "observer_has_emergence_classification": "emergence" in reports[-1],
        "causal_state_identical_without_observer": _causal_digest(control) == _causal_digest(observed),
        "world_identical": control.world_state() == observed.world_state(),
        "matter_identical": control.matter_state() == observed.matter_state(),
        "producer_identical": control.ecology_state() == observed.ecology_state(),
        "consumer_identical": control.consumer_state() == observed.consumer_state(),
        "human_identical": control.human_state() == observed.human_state(),
        "ledger_digest_identical": control.ledger.digest() == observed.ledger.digest(),
        "ledger_valid": control.ledger.verify_chain() and observed.ledger.verify_chain(),
        "observer_not_authority": all(
            "observer" not in authority_id.lower()
            for authority_id in observed.fabric.authority_ids
        ),
    }

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print("G9_FINAL_REPORT:", reports[-1])

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("G9_GATE_FAIL:", ", ".join(failed))
        return 1

    print("G9_GATE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
