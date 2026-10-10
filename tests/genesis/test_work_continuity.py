"""Observer parity and correctly counted departure/return versus repeated work."""

from dataclasses import replace
from types import SimpleNamespace

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import biology, interactions as cap
from qualification.genesis.discovery import config_for
from qualification.genesis.work_continuity import Continuity


def test_continuity_observer_preserves_full_state_and_restores_hooks():
    config = replace(config_for('agentus-demography-a', True), agentus_local_work_enabled=True,
                     agentus_surface_work_enabled=True)
    observed = GenesisSimulation(config)
    original = (biology.choose_destination, cap.choose, cap.execute)
    observer = Continuity()
    observer.install()
    try:
        for day in range(1, 16):
            observer.day = day
            observed.run(1)
    finally:
        observer.uninstall()
    assert original == (biology.choose_destination, cap.choose, cap.execute)
    plain = GenesisSimulation(config)
    plain.run(15)
    assert observed.snapshot() == plain.snapshot()
    assert observed.ledger.digest() == plain.ledger.digest()
    assert observed.ledger.verify_chain()


def test_own_progress_departure_and_return_are_distinct_events():
    observer = Continuity()
    ctx = SimpleNamespace(agent_id='a', xy=(1, 2), pcell={'loose_material_elements_kg': {'C': .25}})
    observer.day = 1
    observer.after_action(ctx, 'apply_force:woody|none', (0, 0), {})
    perception = {'origin': [1, 2], 'cells': [{'x': 1, 'y': 2, 'food_kg': 1, 'water_kg': 2}],
                  'forage_need_kg': .5, 'water_need_kg': 1}
    cognition = {'memory': {'locations': {'1,2': {'food_kg': 1}}}}
    observer.day = 2
    observer.movement({'id': 'a'}, perception, cognition, (2, 2))
    observer.day = 3
    observer.movement({'id': 'b'}, perception, cognition, (1, 2))
    assert observer.result()['sites_returned_to'] == 0
    observer.day = 4
    observer.movement({'id': 'a'}, perception, cognition, (1, 2))
    observer.after_action(ctx, 'apply_force:woody|none', (.1, 0), {})
    result = observer.result()
    assert result['sites_returned_to'] == result['sites_worked_on_multiple_days'] == 1
    assert result['counts']['departures_from_own_wood_worksite'] == 1
    assert result['counts']['returns_to_own_wood_worksite'] == 1
    assert result['counts']['departures_with_location_memory'] == 1
    assert result['counts'].get('departures_with_material_location_memory', 0) == 0


def test_pool_options_are_counted_once_per_agent_day_and_per_decision():
    observer = Continuity()
    observer.day = 2
    key = 'arrange:loose_wood|none'
    ctx = SimpleNamespace(agent_id='a', xy=(0, 0), pcell={},
                          human={'energy': 1000, 'body_water_kg': 10,
                                 'cognition': {'affordance_values': {key: {'v': -.1}}}},
                          profile={'basal_energy_kcal_per_tick': 100, 'water_loss_per_tick_kg': 1,
                                   'water_capacity_kg': 10, 'min_water_fraction': .5})
    option = (key, {'verb': 'pool', 'sequence': ('arrange',)})
    observer.observe_options(ctx, [option], None)
    observer.observe_options(ctx, [option], option)
    result = observer.result()
    assert result['option_decisions'][key] == 2
    assert result['selected_decisions'][key] == 1
    assert result['counts']['offered:' + key] == 1
    assert result['counts']['nonpositive_offered:' + key] == 1
    assert result['counts']['reserve_ready_offered:' + key] == 1


def test_removed_surface_reacquisition_requires_own_successful_grasp():
    observer = Continuity()
    observer.day = 2
    ground = {'id': 's', 'material': 'surface', 'holder': None, 'worn': False}
    ctx = SimpleNamespace(agent_id='a', humans={'objects': [ground]})
    observer.surface_action(ctx, {'verb': 'remove_surface'}, dict(ground, holder='a', worn=True))
    observer.day = 3
    # A failed grasp does not count, nor does another individual's grasp.
    observer.surface_action(ctx, {'verb': 'grasp_object'}, dict(ground))
    assert observer.counts['own_removed_surface_reacquisitions'] == 0
    prior = dict(ground)
    ground['holder'] = 'b'
    observer.surface_action(SimpleNamespace(agent_id='b', humans=ctx.humans), {'verb': 'grasp_object'}, prior)
    assert observer.counts['own_removed_surface_reacquisitions'] == 0
    ground['holder'] = 'a'
    observer.surface_action(ctx, {'verb': 'grasp_object'}, prior)
    assert observer.counts['own_removed_surface_reacquisitions'] == 1
    assert observer.counts['own_removed_surface_reacquisitions_on_later_day'] == 1
