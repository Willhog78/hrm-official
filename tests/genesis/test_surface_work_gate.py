"""The controlled wood probe must not become a persistent action policy."""

from hrm_genesis.human import interactions as cap
from qualification.genesis.run_surface_work_gate import controlled_wood


def test_controlled_wood_restores_policy_and_keeps_live_physical_budget():
    original = cap.choose
    result = controlled_wood('agentus-demography-a', days=3)
    assert cap.choose is original
    assert result['controlled_action_selection'] and not result['autonomous_discovery_claim']
    assert result['ledger_valid']
    assert sum(result['selected_actions'].values()) <= 3 * result['days']
    assert max(abs(v) for v in result['conservation'].values()) < 1e-9
