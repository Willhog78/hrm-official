"""Delayed returns require surviving own physical provenance, not a time trace."""

from copy import deepcopy
import json

import pytest

from hrm_genesis.human import interactions as cap
from hrm_genesis.human import transitions as tm
from hrm_genesis.human.biology import _apply_physiology
from test_micro_sequence_valuation import scene, context, act, surface


def delayed_scene():
    sc = scene()
    sc.humans['transition_model'] = tm.DELAYED_MODEL
    return sc


def heat(sc, epoch, ctx=None, temperature=0.0):
    local = ctx or context(sc, epoch, temperature)
    arrangement, insulation = cap.prepare_thermal_trials(
        sc.humans, sc.agent, local.pcell, epoch, local.profile, ctx)
    before = deepcopy(sc.agent)
    measured, plain = deepcopy(before), deepcopy(before)
    worn = cap.insulation_c(sc.humans, sc.agent['id'])
    _apply_physiology(measured, local.wcell, False, local.profile, local.pcell,
                      insulation_c=worn, record_arrangement_benefit=True,
                      arrangement_reference=arrangement, insulation_reference_c=insulation)
    _apply_physiology(plain, local.wcell, False, local.profile, local.pcell, insulation_c=worn)
    gains = (measured.pop('insulation_saving_kcal', 0.0), measured.pop('arrangement_saving_kcal'))
    plain.pop('insulation_saving_kcal', None)
    assert measured == plain  # attribution cannot change any physical result
    sc.agent.clear()
    sc.agent.update(measured)
    cap.settle_thermal_trials(sc.humans, sc.agent, epoch, *gains)
    return gains


def wear(sc, epoch=1, area=0.015):
    sc.humans['objects'] = [dict(surface(sc), area_m2=area)]
    ctx = context(sc, epoch, temperature=0.0)
    act(ctx, 'grasp:surface|none', {'verb': 'grasp_object', 'id': 'surface'})
    result = act(ctx, 'wear:surface|held', {'verb': 'wear', 'id': 'surface'})
    cap.learn_from_tick(ctx, [])
    return ctx, result['transition_edge']


def value(sc, edge_id):
    return next(e.get('gain_sum_basal', 0) for e in sc.agent['cognition']['transition_memory']['edges']
                if e['id'] == edge_id)


def arrange(sc, epoch=1):
    sc.set_pool(0, 0, 'woody_elements_kg', 10.0)
    ctx = context(sc, epoch, temperature=0.0)
    act(ctx, 'apply_force:woody|none', {'verb': 'pool', 'sequence': ('apply_force',)})
    result = act(ctx, 'arrange:loose_wood|none', {'verb': 'pool', 'sequence': ('arrange',)})
    cap.learn_from_tick(ctx, [])
    return ctx, result['transition_edge']


def test_actual_later_warmth_accumulates_with_discount_and_no_new_attempts():
    sc = delayed_scene()
    ctx, eid = wear(sc)
    day1, _ = heat(sc, 1, ctx)
    assert 0 < day1 < 4  # first tick does not repay wear's physical cost
    before = value(sc, eid)
    day2, _ = heat(sc, 2)
    assert value(sc, eid) == pytest.approx(before + day2 * tm.THERMAL_DISCOUNT / 2000, abs=1e-10)
    n = next(e['n'] for e in sc.agent['cognition']['transition_memory']['edges'] if e['id'] == eid)
    assert n == 1
    snapshot = deepcopy(sc.agent)
    cap.settle_thermal_trials(sc.humans, sc.agent, 2, day2, 0)
    assert sc.agent == snapshot  # duplicate daily settlement, including across fresh contexts


def test_delayed_experience_can_repay_a_chain_that_one_tick_cannot():
    sc = delayed_scene()
    for trial in range(8):
        epoch = 1 + trial * tm.THERMAL_HORIZON
        sc.set_agent(0, 0, energy=10000.0)
        ctx, eid = wear(sc, epoch)
        heat(sc, epoch, ctx)
        for offset in range(1, tm.THERMAL_HORIZON):
            heat(sc, epoch + offset)
    first = next(e for e in sc.agent['cognition']['transition_memory']['edges']
                 if e['act'] == 'grasp:surface|none')['before']
    assert tm.action_values(sc.agent['cognition'], first, 2000, depth=1)['grasp:surface|none'] < 0
    assert tm.action_values(sc.agent['cognition'], first, 2000)['grasp:surface|none'] > 0
    sc.set_agent(0, 0, energy=10000.0)
    sc.humans['objects'] = [dict(surface(sc), area_m2=0.015)]
    ctx = context(sc, 257, temperature=0.0)
    assert cap.choose(ctx, cap.enumerate_affordances(ctx), 0, False)[0] == 'grasp:surface|none'


def test_trial_expires_and_cannot_survive_forgotten_origin():
    sc = delayed_scene()
    ctx, eid = wear(sc)
    heat(sc, 1, ctx)
    initial = value(sc, eid)
    heat(sc, 1 + tm.THERMAL_HORIZON)
    assert value(sc, eid) == initial and not sc.agent['thermal_trials']
    fresh = delayed_scene()
    ctx, _ = wear(fresh)
    heat(fresh, 1, ctx)
    fresh.agent['cognition']['transition_memory']['edges'] = []
    heat(fresh, 2)
    assert not fresh.agent['thermal_trials']


def test_removed_or_transferred_worn_material_ends_original_credit():
    sc = delayed_scene()
    ctx, eid = wear(sc)
    heat(sc, 1, ctx)
    initial = value(sc, eid)
    sc.humans['objects'][0]['holder'] = 'peer'
    heat(sc, 2)
    assert value(sc, eid) == initial and not sc.agent['thermal_trials']
    sc.humans['objects'][0]['holder'] = sc.agent['id']
    heat(sc, 3)
    assert value(sc, eid) == initial  # returning it does not resurrect the trial


def test_material_decay_reduces_measured_return_and_hot_weather_pays_zero():
    sc = delayed_scene()
    ctx, eid = wear(sc)
    first, _ = heat(sc, 1, ctx)
    sc.humans['objects'][0]['cohesion'] *= 0.5
    second, _ = heat(sc, 2)
    assert second == pytest.approx(first * 0.5, abs=1e-9)
    initial = value(sc, eid)
    assert heat(sc, 3, temperature=40) == (0, 0)
    assert value(sc, eid) == initial


def test_arranged_return_requires_unchanged_local_contribution():
    sc = delayed_scene()
    ctx, eid = arrange(sc)
    _, first = heat(sc, 1, ctx)
    initial = value(sc, eid)
    _, later = heat(sc, 2)
    assert first > 0 and later == first and value(sc, eid) > initial
    sc.agent['x'] = 1
    # Construct a context at the new actual cell, without reading the old cell.
    moved = context(sc, 3, temperature=0.0)
    moved.pcell = sc._p(1, 0)
    heat(sc, 3, moved)
    initial = value(sc, eid)
    sc.agent['x'] = 0
    heat(sc, 4)
    assert value(sc, eid) == initial and not sc.agent['thermal_trials']


def test_intervention_even_if_restored_invalidates_arrangement_provenance():
    sc = delayed_scene()
    ctx, eid = arrange(sc)
    heat(sc, 1, ctx)
    initial = value(sc, eid)
    saved = cap._thermal_arrangement(ctx.pcell)
    peer = deepcopy(sc.agent)
    peer['id'] = 'peer'
    other = context(sc, 2, temperature=0.0)
    other.human = peer
    act(other, 'separate:arranged_wood|none', {'verb': 'pool', 'sequence': ('separate',)})
    ctx.pcell.update(saved)  # even restoring identical mass and shape cannot erase intervention
    heat(sc, 2)
    assert value(sc, eid) == initial and not sc.agent['thermal_trials']


def test_passive_occupant_has_no_origin_and_minor_addition_cannot_claim_old_cover():
    sc = delayed_scene()
    ctx, _ = arrange(sc)
    heat(sc, 1, ctx)
    peer = deepcopy(sc.agent)
    peer['id'] = 'peer'
    peer.pop('thermal_trials')
    peer.pop('thermal_settled_epoch')
    before = deepcopy(peer['cognition'])
    refs = cap.prepare_thermal_trials(sc.humans, peer, ctx.pcell, 2, ctx.profile)
    assert refs == (cap._thermal_arrangement(ctx.pcell), 0)
    cap.settle_thermal_trials(sc.humans, peer, 2, 0, 0)
    assert peer['cognition'] == before
    # Subsequent own addition receives only its increment, not the older trial's payoff.
    sc._p(0, 0)['loose_material_elements_kg'] = {'C': 0.25}
    later = context(sc, 2, temperature=0.0)
    out = act(later, 'arrange:loose_wood|none', {'verb': 'pool', 'sequence': ('arrange',)})
    refs = cap.prepare_thermal_trials(sc.humans, sc.agent, later.pcell, 2, later.profile, later)
    assert refs[0] == later.arrangement_before
    assert sc.agent['thermal_trials']['arrangement']['started'] == 2
    assert sc.agent['thermal_trials']['arrangement']['edges'] == [out['transition_edge']]


def test_backend_trials_do_not_enter_cognition_or_perceptual_projection():
    sc = delayed_scene()
    ctx, _ = wear(sc)
    prior = cap._transition_perception(ctx)
    cap.prepare_thermal_trials(sc.humans, sc.agent, ctx.pcell, 1, ctx.profile, ctx)
    assert cap._transition_perception(ctx) == prior
    assert 'thermal_trials' not in sc.agent['cognition']
    assert len(sc.agent['thermal_trials']) <= 2


def test_different_age_worn_and_arranged_trials_share_one_daily_budget():
    sc = delayed_scene()
    ctx, arranged_edge = arrange(sc)
    heat(sc, 1, ctx)
    sc.humans['objects'] = [dict(surface(sc), holder=sc.agent['id'], area_m2=1.8)]
    later = context(sc, 2, temperature=-25.0)
    out = act(later, 'wear:surface|held', {'verb': 'wear', 'id': 'surface'})
    prior_cover, prior_worn = value(sc, arranged_edge), value(sc, out['transition_edge'])
    worn, cover = heat(sc, 2, later)
    assert len(sc.agent['thermal_trials']) == 2
    bare, protected = deepcopy(sc.agent), deepcopy(sc.agent)
    _apply_physiology(bare, later.wcell, False, later.profile, {})
    _apply_physiology(protected, later.wcell, False, later.profile, later.pcell,
                      insulation_c=cap.insulation_c(sc.humans, sc.agent['id']))
    assert worn + cover <= protected['energy'] - bare['energy'] + 1e-9
    gain = (value(sc, arranged_edge) - prior_cover + value(sc, out['transition_edge']) - prior_worn) * 2000
    assert gain <= worn + cover + 1e-7


def test_live_biology_settles_active_trials_and_serialized_replay_is_exact():
    sc = delayed_scene()
    ctx, eid = wear(sc)
    heat(sc, 1, ctx)
    initial = value(sc, eid)
    for cell in sc.world['cells']:
        cell['temperature'] = 0.0
    sc.set_pool(0, 0, 'plant_elements_kg', 100.0)
    for cell in sc.matter['cells']:
        cell['soil_water_kg'] = 1000.0
    sc.epoch = 2
    restored = deepcopy(sc)
    for name in ('humans', 'producers', 'matter', 'world', 'consumers'):
        setattr(restored, name, json.loads(json.dumps(getattr(sc, name))))
    restored.agent = next(p for p in restored.humans['humans'] if p['id'] == sc.agent['id'])
    sc.step(4)
    restored.step(4)
    assert sc.agent is not None and value(sc, eid) > initial
    for name in ('humans', 'producers', 'matter', 'world', 'consumers'):
        assert getattr(restored, name) == getattr(sc, name)
    assert sc.agent['thermal_settled_epoch'] == 5
    assert 'arrangement_saving_kcal' not in sc.agent
    assert 'insulation_saving_kcal' not in sc.agent
