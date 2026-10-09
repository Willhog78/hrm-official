"""Experienced transitions must remain bounded, local and write-only."""

from dataclasses import replace
import json

import pytest

from _scenario import Scenario
from hrm_genesis import GenesisConfig
from hrm_genesis.human import interactions as cap
from hrm_genesis.human import transitions as tm


def context(sc, epoch=1):
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0),
                       sc._p(*sc.xy), sc.carcass(*sc.xy), sc.matter['lithic_cells'],
                       sc.world['cells'][0], sc.consumers, epoch)


def enabled_scenario():
    sc = Scenario(capacities=True)
    sc.humans['transition_model'] = tm.MODEL
    return sc


def test_disabled_mode_records_nothing_and_keeps_legacy_fingerprint():
    sc = Scenario(capacities=True)
    sc.add_stone(0, 0, 'stone', m=0.6)
    cap.execute(context(sc), 'grasp:stone_heavy|none', {'verb': 'grasp_natural', 'id': 'stone'})
    assert 'transition_memory' not in sc.agent['cognition']
    assert 'agentus_transition_model' not in sc.config.canonical()
    assert replace(sc.config, agentus_transition_model='none').fingerprint() == sc.config.fingerprint()
    assert replace(sc.config, agentus_transition_model=tm.MODEL).fingerprint() != sc.config.fingerprint()
    with pytest.raises(ValueError, match='unknown agentus_transition_model'):
        replace(sc.config, agentus_transition_model='recipe')
    with pytest.raises(ValueError, match='requires agentus_capacities_enabled'):
        GenesisConfig(agentus_transition_model=tm.MODEL)


def test_grasp_remembers_the_state_change_that_enables_a_later_strike():
    sc = enabled_scenario()
    sc.add_stone(0, 0, 'first', m=0.6)
    sc.add_stone(0, 0, 'second', m=0.8)
    ctx = context(sc)
    energy = sc.agent['energy']
    out = cap.execute(ctx, 'grasp:stone_heavy|none', {'verb': 'grasp_natural', 'id': 'first'})
    edge = sc.agent['cognition']['transition_memory']['edges'][0]
    assert edge['before']['held'] == []
    assert edge['after']['held'][0][0] == 'stone_heavy'
    assert 'strike:stone_heavy|stone_heavy' in edge['enabled']
    assert edge['effort_kcal'] == pytest.approx(energy - sc.agent['energy'])
    assert edge['effort_kcal'] == out['effort_kcal']
    assert 'v' not in edge and not sc.agent['cognition']['affordance_values']
    cap.execute(ctx, 'release:stone_heavy|none', {'verb': 'release', 'id': 'first'})
    edges = sc.agent['cognition']['transition_memory']['edges']
    assert edges[0]['after'] == edges[1]['before']
    assert 'strike:stone_heavy|stone_heavy' in edges[1]['disabled']


def test_bulk_force_then_arrangement_records_physical_geometry_without_a_label():
    sc = enabled_scenario()
    sc.set_pool(0, 0, 'woody_elements_kg', 10.0)
    ctx = context(sc)
    cap.execute(ctx, 'apply_force:woody|none', {'verb': 'pool', 'sequence': ('apply_force',)})
    cap.execute(ctx, 'arrange:loose_wood|none', {'verb': 'pool', 'sequence': ('arrange',)})
    a, b = sc.agent['cognition']['transition_memory']['edges']
    assert 'arrange:loose_wood|none' in a['enabled']
    assert a['after'] == b['before']
    assert b['before']['geometry'] != b['after']['geometry']
    assert b['effort_kcal'] > 0
    assert 'shelter' not in json.dumps(sc.agent['cognition']['transition_memory'])


def test_wearing_is_a_transition_without_a_granted_warmth_reward():
    sc = enabled_scenario()
    fiber = {'material': 'fiber', 'source': 'plant', 'elements_kg': {'C': 0.1},
             'length_m': 1.0, 'diameter_m': 0.01, 'integrity': 1.0, 'flexibility': 0.8}
    surface = {'id': 'cloth', 'material': 'surface', 'strands': [fiber],
               'area_m2': 0.5, 'cohesion': 0.8, 'x': 0, 'y': 0,
               'holder': sc.agent['id'], 'worn': False}
    sc.humans['objects'].append(surface)
    cap.execute(context(sc), 'wear:surface|held', {'verb': 'wear', 'id': 'cloth'})
    edge = sc.agent['cognition']['transition_memory']['edges'][0]
    assert edge['before']['worn'] == [] and edge['after']['worn']
    assert edge['after']['held'] == []
    assert edge['effort_kcal'] == 4.0
    assert not sc.agent['cognition']['affordance_values']


def test_remote_state_peer_inventory_and_internal_values_are_not_recorded():
    sc = enabled_scenario()
    ctx = context(sc)
    before = cap._transition_perception(ctx)
    sc.add_stone(3, 0, 'SECRET_REMOTE_STONE', m=7.0)
    sc.set_pool(3, 0, 'woody_elements_kg', 5000.0)
    sc.add_agent('SECRET_PEER', 0, 0)
    sc.humans['objects'].append({'id': 'SECRET_HELD_STONE', 'material': 'stone',
                                'fragment': {'id': 'SECRET_FRAGMENT', 'lith': 'basaltic', 'm': 1.0, 's': 0.0, 'e': 1.0},
                                'x': 0, 'y': 0, 'holder': 'SECRET_PEER', 'worn': False})
    sc.agent['cognition']['affordance_values']['SECRET_REWARD'] = {'v': 99, 'n': 1}
    assert cap._transition_perception(ctx) == before
    assert 'SECRET' not in json.dumps(before)


def test_equivalent_visible_objects_are_recognized_without_identity_or_history():
    sc = enabled_scenario()
    sc.add_stone(0, 0, 'one', m=0.6)
    ctx = context(sc)
    initial = cap._transition_perception(ctx)
    sc.matter['lithic_cells']['0,0'][0]['id'] = 'entirely-different'
    assert cap._transition_perception(ctx) == initial
    cap.execute(ctx, 'grasp:stone_heavy|none', {'verb': 'grasp_natural', 'id': 'entirely-different'})
    held = cap._transition_perception(ctx)
    sc.humans['objects'][0]['history'] = ['arbitrary-hidden-history']
    assert cap._transition_perception(ctx) == held


def test_failed_attempts_keep_costs_without_inventing_a_changed_state():
    sc = enabled_scenario()
    ctx = context(sc)
    for epoch in range(1, 4):
        ctx.epoch = epoch
        cap.execute(ctx, 'release:stone_heavy|none', {'verb': 'release', 'id': 'absent'})
    edge = sc.agent['cognition']['transition_memory']['edges'][0]
    assert edge['before'] == edge['after']
    assert edge['n'] == 3 and edge['effort_kcal'] > 0
    assert not edge['enabled'] and not edge['disabled']
    assert not sc.agent['cognition']['affordance_values']


def test_alternative_outcomes_stay_separate_and_costs_average_per_outcome():
    cognition = {}
    before, changed = {'acts': ['manipulate']}, {'acts': ['manipulate', 'release']}
    tm.record(cognition, before, 'manipulate', changed, 4.0, 0.02, 1)
    tm.record(cognition, before, 'manipulate', before, 2.0, 0.0, 2)
    tm.record(cognition, before, 'manipulate', changed, 8.0, 0.0, 3)
    a, b = cognition['transition_memory']['edges']
    assert a['after'] == before and a['n'] == 1
    assert b['after'] == changed and b['n'] == 2
    assert b['effort_kcal'] == 6.0 and b['injury'] == 0.01
    changed['acts'].append('later-mutation')
    assert 'later-mutation' not in b['after']['acts']


def test_memory_is_bounded_and_idle_ticks_age_it_out():
    cognition = {}
    for i in range(tm.MAX_TRANSITIONS + 10):
        tm.record(cognition, {'acts': ['a'], 'shape': i}, 'a', {'acts': ['b']}, 2, 0, i)
    memory = cognition['transition_memory']
    assert len(memory['edges']) == tm.MAX_TRANSITIONS
    assert len(memory['recent']) == tm.RECENT_LENGTH
    assert min(e['before']['shape'] for e in memory['edges']) == 10
    sc = enabled_scenario()
    sc.agent['cognition'].update(cognition)
    sc.agent['fatigue'] = 0.9
    cap.run_interactions(sc.humans, sc.agent, sc.profile, sc._p(0, 0), sc.carcass(0, 0),
                         sc.matter['lithic_cells'], sc.world['cells'][0], sc.consumers,
                         tm.MAX_TRANSITIONS + 10 + tm.FORGET_AFTER_TICKS, False)
    assert sc.agent['cognition']['transition_memory']['edges'] == []
    assert sc.agent['cognition']['transition_memory']['recent'] == []


def test_clutter_projection_is_bounded_and_sorted():
    sc = enabled_scenario()
    for i in range(100):
        sc.add_stone(0, 0, f'stone-{i}', m=0.6)
    state = cap._transition_perception(context(sc))
    assert len(state['ground']) <= tm.MAX_OBJECT_FORMS
    assert state['ground'][0][-1] == 3
    assert len(state['acts']) <= tm.MAX_ACTS
