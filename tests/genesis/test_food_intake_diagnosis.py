import hrm_genesis.runner as runner_module
from hrm_genesis import GenesisSimulation
from hrm_genesis.human import biology

from experiments.genesis import run_agentus_food_intake_diagnosis as diagnosis


def test_instrumentation_is_read_only_and_restored():
    plain = GenesisSimulation(diagnosis._config("agentus-demography-a"))
    plain.run(12)

    originals = (biology._eat, biology._apply_physiology, runner_module.evolve_humans)
    recorder = diagnosis.Recorder()
    with diagnosis.instrumented(recorder):
        traced = GenesisSimulation(diagnosis._config("agentus-demography-a"))
        traced.run(12)
    assert (biology._eat, biology._apply_physiology, runner_module.evolve_humans) == originals

    assert recorder.calls == 12
    assert traced.ledger.digest() == plain.ledger.digest()
    assert traced.human_state() == plain.human_state()


def test_adult_energy_budget_closes():
    result = diagnosis.run_seed("agentus-demography-a", days=10)
    adult = result["budgets_by_stage"]["adult"]
    assert adult["energy_change_days"] == adult["person_days"]
    expected = (
        adult["credited_kcal"] + adult["nursing_in_kcal"] - adult["basal_kcal"] - adult["move_kcal"]
        - adult["thermal_kcal"] - adult["effort_kcal"] - adult["nursing_out_kcal"]
    )
    assert abs(adult["energy_change_kcal"] - expected) < 1e-3
