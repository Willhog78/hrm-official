"""Longer procedures require experienced adjacency and physical state progress."""

from copy import deepcopy
import json

from hrm_genesis.human import interactions as cap
from hrm_genesis.human import transitions as tm
from hrm_genesis.human.biology import _apply_physiology
from hrm_genesis.human.diet import forage_at_cell
from test_micro_sequence_valuation import scene, context, act, train_food


def state(i, acts, energy=4, injury=0):
    return {'acts': acts, 'held': [['strand_plant', i + 1]], 'ground': [], 'worn': [],
            'pools': [i], 'geometry': [], 'weather': [0], 'position': [0, 0],
            'access': 0, 'body': [energy, 4, 0, injury]}


def train(steps=6, repeated=False):
    cognition = {}
    keys = ['work' if repeated else f'work{i}' for i in range(steps)]
    states = [state(i, keys[:i + 1]) for i in range(steps + 1)]
    for trial in range(8):
        for i, key in enumerate(keys):
            # First three real attempts on one tick, remaining ones the next.
            epoch = trial * 3 + 1 + i // 3
            before = deepcopy(states[i])
            if i >= 3:
                before['body'][0] = 3
            eid = tm.record(cognition, before, key, states[i + 1], 2, 0, epoch,
                            model=tm.PROCEDURAL_MODEL)
            if i == steps - 1:
                tm.credit(cognition, eid, 1.0)
    return cognition, states[0]


def test_six_step_value_crosses_tick_boundary_without_applying_predicted_state():
    cognition, initial = train()
    before = deepcopy(cognition)
    assert tm.action_values(cognition, initial, 2000)['work0'] > 0
    assert tm.action_values(cognition, initial, 2000, depth=3)['work0'] < 0
    assert tm.action_values(cognition, initial, 2000, depth=100) == tm.action_values(cognition, initial, 2000)
    assert cognition == before


def test_repeated_action_requires_distinct_progress_states_and_observed_links():
    cognition, initial = train(repeated=True)
    assert tm.action_values(cognition, initial, 2000)['work'] > 0
    assert len(cognition['transition_memory']['links']) == 5
    absent = deepcopy(cognition)
    absent['transition_memory']['links'] = []
    assert tm.action_values(absent, initial, 2000)['work'] < 0


def test_one_pair_or_nonconsecutive_experience_cannot_supply_a_procedure():
    cognition = {}
    a, b, c = state(0, ['a']), state(1, ['a', 'b']), state(2, [])
    for trial in range(4):
        tm.record(cognition, a, 'a', b, 10, 0, trial * 5, model=tm.PROCEDURAL_MODEL)
        eid = tm.record(cognition, b, 'b', c, 10, 0, trial * 5 + 3, model=tm.PROCEDURAL_MODEL)
        tm.credit(cognition, eid, 1)
    assert not cognition['transition_memory']['links']
    assert tm.action_values(cognition, a, 2000)['a'] < 0
    tm.record(cognition, a, 'a', b, 10, 0, 30, model=tm.PROCEDURAL_MODEL)
    tm.record(cognition, b, 'b', c, 10, 0, 30, model=tm.PROCEDURAL_MODEL)
    assert tm.action_values(cognition, a, 2000)['a'] < 0


def test_changed_weather_access_and_injury_are_not_normalized_away():
    cognition, initial = train()
    rested = deepcopy(initial)
    rested['body'][:3] = [2, 3, 1]
    assert tm.action_values(cognition, rested, 2000)['work0'] > 0
    for field, new in (('weather', [5]), ('access', 2), ('body', [4, 4, 0, 2])):
        changed = deepcopy(initial)
        changed[field] = new
        assert not tm.action_values(cognition, changed, 2000)


def test_unrelated_material_change_cannot_link_already_possible_rewarded_action():
    cognition = {}
    a = state(0, ['grasp', 'cut'])
    a['held'] = [['stone_edged', 1]]
    b = deepcopy(a)
    b['held'].append(['stone_heavy', 1])
    c = deepcopy(b)
    c['access'] = 1
    for trial in range(4):
        tm.record(cognition, a, 'grasp', b, 10, 0, trial, model=tm.PROCEDURAL_MODEL)
        eid = tm.record(cognition, b, 'cut', c, 10, 0, trial, model=tm.PROCEDURAL_MODEL)
        tm.credit(cognition, eid, 1)
    assert not cognition['transition_memory']['links']
    assert tm.action_values(cognition, a, 2000)['grasp'] < 0


def test_noop_and_closed_cycle_cannot_repeat_terminal_payoff_in_search():
    cognition = {}
    a, b = state(0, ['a', 'b']), state(1, ['a', 'b'])
    for trial in range(8):
        tm.record(cognition, a, 'a', b, 10, 0, trial, model=tm.PROCEDURAL_MODEL)
        eid = tm.record(cognition, b, 'b', a, 10, 0, trial, model=tm.PROCEDURAL_MODEL)
        tm.credit(cognition, eid, 1)
    assert tm.action_values(cognition, a, 2000, depth=2) == tm.action_values(cognition, a, 2000, depth=6)


def test_links_remain_bounded_and_forgetting_removes_dangling_references():
    cognition, initial = train()
    tm.forget(cognition, 500)
    assert not cognition['transition_memory']['edges']
    assert not cognition['transition_memory']['links']
    assert not tm.action_values(cognition, initial, 2000)
    cognition = {}
    for i in range(180):
        before, after = state(i, ['work']), state(i + 1, ['work'])
        tm.record(cognition, before, 'work', after, 1, 0, i // 3, model=tm.PROCEDURAL_MODEL)
    memory = cognition['transition_memory']
    retained = {e['id'] for e in memory['edges']}
    assert len(memory['edges']) <= tm.MAX_TRANSITIONS
    assert len(memory['links']) <= tm.MAX_LINKS
    assert all(link['from'] in retained and link['to'] in retained for link in memory['links'])


def test_live_choice_still_requires_reserves_and_physically_offered_material():
    sc = scene()
    sc.humans['transition_model'] = tm.PROCEDURAL_MODEL
    ctx = train_food(sc)
    assert cap.choose(ctx, cap.enumerate_affordances(ctx), 0, True)[0] == 'grasp:stone_edged|none'
    sc.agent['energy'] = 1000
    before = deepcopy(sc.humans['capacity_stats'].get('sequence_choices', {}))
    cap.choose(ctx, cap.enumerate_affordances(ctx), 0, True)
    assert sc.humans['capacity_stats'].get('sequence_choices', {}) == before
    sc.agent['energy'] = 10000
    sc.humans['objects'] = []
    cap.choose(ctx, cap.enumerate_affordances(ctx), 0, True)
    assert sc.humans['capacity_stats'].get('sequence_choices', {}) == before


def test_link_ages_out_even_when_its_individual_steps_are_reexperienced_separately():
    cognition, _ = train(steps=2)
    a, b = deepcopy(cognition['transition_memory']['edges'][:2])
    tm.record(cognition, a['before'], a['act'], a['after'], 2, 0, 100, model=tm.PROCEDURAL_MODEL)
    tm.record(cognition, b['before'], b['act'], b['after'], 2, 0, 103, model=tm.PROCEDURAL_MODEL)
    tm.forget(cognition, 120)
    assert len(cognition['transition_memory']['edges']) == 2
    assert not cognition['transition_memory']['links']


def reset_stone_opportunity(sc):
    sc.set_agent(0, 0, energy=10000.0)
    sc.set_fresh_tissue(0, 0, 5.0)
    sc.humans['objects'] = []
    sc.matter['lithic_cells'] = {}
    sc.add_stone(0, 0, 'hammer', lith='basaltic', m=1.0, s=0.05, e=1.2)
    sc.add_stone(0, 0, 'core', lith='siliceous_fine', m=0.6, s=0.05, e=1.2)


def stone_experience():
    sc = scene()
    sc.humans['transition_model'] = tm.PROCEDURAL_MODEL
    successes = 0
    for trial in range(40):
        reset_stone_opportunity(sc)
        ctx = context(sc, trial * 2 + 1)
        act(ctx, 'grasp:stone_heavy|none', {'verb': 'grasp_natural', 'id': 'hammer'})
        act(ctx, 'strike:stone_heavy|stone_heavy', {'verb': 'strike_stone', 'tool': 'hammer', 'natural': 'core'})
        edged = next((o for o in sc.humans['objects']
                      if o.get('holder') is None and cap.object_class(o) == 'stone_edged'), None)
        if edged is None:
            cap.learn_from_tick(ctx, [])
            continue
        act(ctx, 'grasp:stone_edged|none', {'verb': 'grasp_object', 'id': edged['id']})
        cap.learn_from_tick(ctx, [])
        sc.agent['energy'] -= ctx.profile['basal_energy_kcal_per_tick']
        _apply_physiology(sc.agent, ctx.wcell, False, ctx.profile, ctx.pcell)
        tomorrow = context(sc, trial * 2 + 2)
        act(tomorrow, 'cut:fresh_tissue|stone_edged', {'verb': 'cut_tissue', 'tool': edged['id']})
        intake = forage_at_cell(sc.agent, tomorrow.pcell, tomorrow.ccell, tomorrow.profile,
                                sc.agent['cognition']['food_values'], (), tomorrow.access_bonus)
        cap.learn_from_tick(tomorrow, intake)
        successes += 1
    return sc, successes


def test_actual_four_action_stone_procedure_survives_body_drift_and_three_action_tick_cap():
    sc, successes = stone_experience()
    assert successes == 21  # actual stochastic fracture, including 19 unpaid outcomes
    cognition = sc.agent['cognition']
    first = next(e for e in cognition['transition_memory']['edges']
                 if e['act'] == 'grasp:stone_heavy|none')['before']
    assert tm.action_values(cognition, first, 2000, depth=3)['grasp:stone_heavy|none'] < 0
    assert tm.action_values(cognition, first, 2000)['grasp:stone_heavy|none'] > 0
    assert tm.action_values({'transition_memory': json.loads(json.dumps(cognition['transition_memory']))},
                            first, 2000) == tm.action_values(cognition, first, 2000)
    reset_stone_opportunity(sc)
    initial = context(sc, 81)
    failed = cap.run_interactions(sc.humans, sc.agent, initial.profile, initial.pcell,
                                  initial.ccell, initial.lithic_cells, initial.wcell,
                                  initial.consumers, 81, True)
    assert [key for key, _ in failed.performed] == [
        'grasp:stone_heavy|none', 'strike:stone_heavy|stone_heavy']
    assert not any(cap.object_class(o) == 'stone_edged' for o in sc.humans['objects'])
    # A failed physical fracture cannot be replaced by its remembered success.
    reset_stone_opportunity(sc)
    initial = context(sc, 83)
    # The actual live loop and chooser select three steps, then wait for the next tick.
    ctx = cap.run_interactions(sc.humans, sc.agent, initial.profile, initial.pcell,
                               initial.ccell, initial.lithic_cells, initial.wcell,
                               initial.consumers, 83, True)
    assert [key for key, _ in ctx.performed] == [
        'grasp:stone_heavy|none', 'strike:stone_heavy|stone_heavy', 'grasp:stone_edged|none']
    cap.learn_from_tick(ctx, [])
    sc.agent['energy'] -= ctx.profile['basal_energy_kcal_per_tick']
    _apply_physiology(sc.agent, ctx.wcell, False, ctx.profile, ctx.pcell)
    tomorrow = context(sc, 84)
    picked = cap.choose(tomorrow, cap.enumerate_affordances(tomorrow), 0, True)
    assert picked[0] == 'cut:fresh_tissue|stone_edged'
    out = act(tomorrow, *picked)
    intake = forage_at_cell(sc.agent, tomorrow.pcell, tomorrow.ccell, tomorrow.profile,
                            sc.agent['cognition']['food_values'], (), tomorrow.access_bonus)
    cap.learn_from_tick(tomorrow, intake)
    assert out['access_bonus_kg'] > 0
    assert any(e.get('gain_sum_basal', 0) > 0 for e in sc.agent['cognition']['transition_memory']['edges']
               if e['id'] == out['transition_edge'])
    assert abs(cap.lithic_inventory_kg(sc.matter, sc.humans) - 1.6) < 1e-12
