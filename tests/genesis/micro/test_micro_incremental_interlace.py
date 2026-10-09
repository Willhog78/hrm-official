"""Accumulated surfaces conserve material and retain old damage/access limits."""

from copy import deepcopy

import pytest

from _scenario import Scenario
from hrm_genesis.human import interactions as cap
from hrm_genesis.human import transitions as tm
from hrm_genesis.matter import objects as mo
from qualification.genesis.material_scale import strand


def scene():
    sc = Scenario(capacities=True)
    sc.humans['surface_work_model'] = 'incremental-interlace-v1'
    sc.humans['transition_model'] = tm.PROCEDURAL_MODEL
    sc.set_agent(0, 0, energy=10000.)
    patch = mo.interlace([strand('plant', f'old-{i}') for i in range(6)], 'patch')
    sc.humans['objects'] = [cap._place(patch, 0, 0, sc.agent['id'])]
    return sc, context(sc)


def context(sc, epoch=1):
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.),
                       sc._p(0, 0), sc.carcass(0, 0), sc.matter['lithic_cells'],
                       sc.world['cells'][0], sc.consumers, epoch)


def add_strands(sc, count=4, **changes):
    for i in range(count):
        obj = strand('plant', f'new-{len(sc.humans["objects"])}-{i}')
        obj.update(changes)
        sc.humans['objects'].append(cap._place(obj, 0, 0, sc.agent['id']))


def test_live_surface_grows_across_many_costed_actions_with_only_current_hand_inputs():
    sc, ctx = scene()
    total_energy = sc.agent['energy']
    spent = 0.
    for epoch in range(1, 25):
        add_strands(sc)
        ctx = context(sc, epoch)
        assert len(ctx.soft_held()) == 5
        before = cap.object_element_totals(sc.humans)
        key = 'interlace:surface+strands|held'
        out = cap.execute(ctx, key, dict(cap.enumerate_affordances(ctx))[key])
        spent += out['effort_kcal']
        assert cap.object_element_totals(sc.humans) == pytest.approx(before)
        patch, = sc.humans['objects']
        assert len(patch['strands']) == 6 + epoch * 4
        assert patch['history'][-1] == key
        assert out['transition_edge']
    assert patch['area_m2'] > .04
    assert spent == 24 * 25
    assert sc.agent['energy'] == pytest.approx(total_energy - spent)


def test_extending_preserves_area_loss_cohesion_and_wetness():
    sc, ctx = scene()
    patch = sc.humans['objects'][0]
    patch['area_m2'] *= .5
    patch['cohesion'] = .6
    patch['wetness'] = .8
    add_strands(sc)
    nominal = mo.interlace(patch['strands'] + sc.humans['objects'][1:], 'nominal')
    cap.execute(ctx, 'interlace:surface+strands|held', dict(cap.enumerate_affordances(ctx))['interlace:surface+strands|held'])
    extended, = sc.humans['objects']
    assert extended['area_m2'] == pytest.approx(nominal['area_m2'] * .5, abs=1e-10)
    assert extended['cohesion'] == .6
    assert extended['wetness'] == .8


def test_failed_extension_costs_effort_and_leaves_damaged_inputs_intact():
    sc, ctx = scene()
    sc.humans['objects'][0]['cohesion'] = .4
    add_strands(sc)
    before = deepcopy(sc.humans['objects'])
    out = cap.execute(ctx, 'interlace:surface+strands|held', dict(cap.enumerate_affordances(ctx))['interlace:surface+strands|held'])
    assert out['unravelled'] and out['effort_kcal'] == 25
    assert sc.humans['objects'] == before


@pytest.mark.parametrize('invalid', ['remote', 'worn', 'duplicate', 'hand_limit', 'carry_limit'])
def test_physical_execution_rechecks_access_and_limits(invalid):
    sc, ctx = scene()
    add_strands(sc)
    spec = dict(cap.enumerate_affordances(ctx))['interlace:surface+strands|held']
    if invalid == 'remote':
        sc.humans['objects'][1]['holder'] = 'someone-else'
    elif invalid == 'worn':
        sc.humans['objects'][0]['worn'] = True
    elif invalid == 'duplicate':
        spec['strands'] = [spec['strands'][0]] * 4
    elif invalid == 'hand_limit':
        add_strands(sc, 2)
    else:
        sc.agent['held_material_elements_kg'] = {'C': 21.}
    before = deepcopy(sc.humans['objects'])
    cap.execute(ctx, 'interlace:surface+strands|held', spec)
    assert sc.humans['objects'] == before


def test_worn_surface_can_be_removed_then_acquired_under_normal_hand_limits():
    sc, ctx = scene()
    patch = sc.humans['objects'][0]
    patch['worn'] = True
    assert cap.insulation_c(sc.humans, sc.agent['id']) > 0
    spec = dict(cap.enumerate_affordances(ctx))['release:surface|worn']
    out = cap.execute(ctx, 'release:surface|worn', spec)
    assert out['effort_kcal'] == 4 and cap.insulation_c(sc.humans, sc.agent['id']) == 0
    assert patch['holder'] is None and not patch['worn']
    grasp = dict(cap.enumerate_affordances(ctx))['grasp:surface|none']
    cap.execute(ctx, 'grasp:surface|none', grasp)
    assert patch['holder'] == sc.agent['id'] and not patch['worn']


def test_legacy_affordances_unchanged_and_extension_cannot_run_without_version():
    sc, ctx = scene()
    add_strands(sc)
    sc.humans.pop('surface_work_model')
    assert 'interlace:surface+strands|held' not in dict(cap.enumerate_affordances(ctx))
    before = deepcopy(sc.humans['objects'])
    cap.execute(ctx, 'interlace:surface+strands|held', {'verb': 'extend_surface', 'id': 'patch',
                                                    'strands': [o['id'] for o in sc.humans['objects'][1:]]})
    assert sc.humans['objects'] == before
