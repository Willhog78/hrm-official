"""The plant mass ledger closes and does not change the world."""

from __future__ import annotations

import pytest

import hrm_genesis.runner as runner
from hrm_genesis import GenesisSimulation
from hrm_genesis.ecology import plants
from qualification.genesis.plant_ledger import POOLS, PlantLedger, control_config, pool_totals
from qualification.genesis.tier_observer import build_config

SEED = "agentus-demography-a"
DAYS = 12


@pytest.mark.parametrize("control", [False, True])
def test_ledger_closes_and_is_read_only(control):
    config = control_config(SEED, "v1") if control else build_config(SEED, "v1")
    ledger = PlantLedger()
    ledger.install()
    try:
        sim = GenesisSimulation(config)
        start = pool_totals(sim.ecology_state())
        sim.run(DAYS)
        end = pool_totals(sim.ecology_state())
        f = ledger.flows
    finally:
        ledger.uninstall()
    assert plants.FLOW_OBSERVER is None and runner.evolve_producers is plants.evolve_producers
    for pool in POOLS:
        moved = sum(f[f"{label}_net_{pool}"] for label in ("producer_step", "animals", "agentus"))
        assert end[pool] - start[pool] == pytest.approx(moved, abs=1e-6)
    edible = f["growth_edible"] + f["germination"] - f["mortality_edible"] - f["reproduction"]
    assert f["producer_step_net_plant"] == pytest.approx(edible, abs=1e-6)
    if control:
        assert not config.consumer_ecology_enabled and not config.human_biology_enabled
        assert f["animals_net_plant"] == 0.0 and f["agentus_net_plant"] == 0.0
    unobserved = GenesisSimulation(config)
    unobserved.run(DAYS)
    assert unobserved.ledger.digest() == sim.ledger.digest()
