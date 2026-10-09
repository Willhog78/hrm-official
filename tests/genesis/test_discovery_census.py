"""Observation must preserve physics and count exposure separately from use."""

from qualification.genesis.discovery import Census, run_one
from hrm_genesis.human import interactions as cap
from hrm_genesis.human import transitions as tm
from hrm_genesis.human import biology


def test_census_is_invisible_to_full_weather_simulation():
    observed = run_one('agentus-demography-a', True, 12, True, True)
    plain = run_one('agentus-demography-a', True, 12, False)
    for field in ('ledger_digest', 'fingerprint', 'alive', 'births', 'capacity_stats', 'conservation'):
        assert observed[field] == plain[field]
    assert observed['ledger_valid'] and plain['ledger_valid']
    assert observed['max_interactions_per_agent_tick'] <= 3


def test_census_restores_all_wrapped_functions():
    names = [(cap, 'choose'), (cap, 'execute'), (cap, 'learn_from_tick'),
             (cap, 'settle_thermal_trials'), (tm, 'credit'), (biology, '_apply_physiology')]
    original = [getattr(module, name) for module, name in names]
    census = Census(thermal_exposure=True)
    try:
        census.install()
        assert all(getattr(module, name) is not fn for (module, name), fn in zip(names, original))
    finally:
        census.uninstall()
    assert all(getattr(module, name) is fn for (module, name), fn in zip(names, original))


