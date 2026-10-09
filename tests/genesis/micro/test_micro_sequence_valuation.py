"""Conditional sequence value must come from actual, causally relevant benefit."""

from copy import deepcopy
from dataclasses import replace

import pytest

from _scenario import Scenario
from hrm_genesis import GenesisConfig
from hrm_genesis.human import interactions as cap
from hrm_genesis.human import transitions as tm
from hrm_genesis.human.biology import _apply_physiology
from hrm_genesis.human.diet import forage_at_cell
from hrm_genesis.matter import objects as mo


def scene():
    sc = Scenario(capacities=True)
    sc.humans['transition_model'] = tm.VALUED_MODEL
    sc.set_agent(0, 0, energy=10000.0)
    sc.set_fresh_tissue(0, 0, 5.0)
    sc.agent['cognition']['food_values']['fresh_tissue'] = 4000.0
    return sc


def context(sc, epoch=1, temperature=22.0):
    profile = dict(sc.profile, development_scale=1.0,
                   energy_store_capacity_kcal=sc.profile['energy_capacity_kcal'])
    world = dict(sc.world['cells'][0], temperature=temperature)
    return cap.Context(sc.humans, sc.agent, profile, sc._p(0, 0), sc.carcass(0, 0),
                       sc.matter['lithic_cells'], world, sc.consumers, epoch)


def act(ctx, key, spec):
    out = cap.execute(ctx, key, spec)
    ctx.performed.append((key, out))
    return out


def edge(sc):
    return {'id': 'edge', 'material': 'stone',
            'fragment': {'id': 'edge', 'lith': 'siliceous_fine', 'm': 0.1, 's': 0.85, 'e': 3.0},
            'x': 0, 'y': 0, 'holder': None, 'worn': False}


def reset_food_trial(sc):
    # Independent controlled opportunities, retaining only individual memory.
    sc.set_agent(0, 0, energy=10000.0)
    sc.set_fresh_tissue(0, 0, 5.0)
    sc.humans['objects'] = [edge(sc)]


def train_food(sc, trials=3):
    for day in range(1, trials + 1):
        reset_food_trial(sc)
        ctx = context(sc, day)
        act(ctx, 'grasp:stone_edged|none', {'verb': 'grasp_object', 'id': 'edge'})
        act(ctx, 'cut:fresh_tissue|stone_edged', {'verb': 'cut_tissue', 'tool': 'edge'})
        intake = forage_at_cell(sc.agent, ctx.pcell, ctx.ccell, ctx.profile,
                                sc.agent['cognition']['food_values'], (), ctx.access_bonus)
        cap.learn_from_tick(ctx, intake)
    reset_food_trial(sc)
    return context(sc, trials + 1)


def test_preparation_becomes_worth_trying_only_through_an_experienced_paid_chain():
    sc = scene()
    ctx = train_food(sc)
    before = cap._transition_perception(ctx)
    direct = tm.action_values(sc.agent['cognition'], before, 2000.0, depth=1)
    chained = tm.action_values(sc.agent['cognition'], before, 2000.0)
    assert direct['grasp:stone_edged|none'] < 0
    assert chained['grasp:stone_edged|none'] > 0
    assert sc.agent['cognition']['affordance_values']['grasp:stone_edged|none']['v'] < 0
    options = cap.enumerate_affordances(ctx)
    assert cap.choose(ctx, options, 0, True)[0] == 'grasp:stone_edged|none'
    assert sc.humans['capacity_stats']['sequence_choices']['grasp:stone_edged|none'] == 1


def test_an_unrelated_preceding_action_gets_no_credit_from_a_meal():
    sc = scene()
    for day in range(1, 4):
        sc.set_agent(0, 0, energy=10000.0)
        sc.set_fresh_tissue(0, 0, 5.0)
        cutting = edge(sc)
        cutting['holder'] = sc.agent['id']
        sc.humans['objects'] = [cutting]
        sc.matter['lithic_cells'] = {'0,0': [{'id': 'heavy', 'lith': 'basaltic', 'm': 0.6, 's': 0.0, 'e': 1.0}]}
        ctx = context(sc, day)
        act(ctx, 'grasp:stone_heavy|none', {'verb': 'grasp_natural', 'id': 'heavy'})
        act(ctx, 'cut:fresh_tissue|stone_edged', {'verb': 'cut_tissue', 'tool': 'edge'})
        intake = forage_at_cell(sc.agent, ctx.pcell, ctx.ccell, ctx.profile,
                                sc.agent['cognition']['food_values'], (), ctx.access_bonus)
        cap.learn_from_tick(ctx, intake)
    memory = sc.agent['cognition']['transition_memory']
    grasp = next(e for e in memory['edges'] if e['act'] == 'grasp:stone_heavy|none')
    assert 'cut:fresh_tissue|stone_edged' not in grasp['enabled']
    assert grasp.get('gain_sum_basal', 0.0) == 0
    assert tm.action_values(sc.agent['cognition'], grasp['before'], 2000)['grasp:stone_heavy|none'] < 0
    assert sc.agent['cognition']['affordance_values']['grasp:stone_heavy|none']['v'] < 0


def test_cost_without_received_food_never_becomes_a_positive_sequence():
    sc = scene()
    ctx = train_food(sc, trials=1)
    assert not tm.action_values(sc.agent['cognition'], cap._transition_perception(ctx), 2000)
    for day in range(5, 8):
        reset_food_trial(sc)
        ctx = context(sc, day)
        act(ctx, 'grasp:stone_edged|none', {'verb': 'grasp_object', 'id': 'edge'})
        act(ctx, 'cut:fresh_tissue|stone_edged', {'verb': 'cut_tissue', 'tool': 'edge'})
        cap.learn_from_tick(ctx, [])
    # A separate empty-payoff history cannot get useful value from manipulating material.
    empty = scene()
    for day in range(1, 4):
        reset_food_trial(empty)
        ctx = context(empty, day)
        act(ctx, 'grasp:stone_edged|none', {'verb': 'grasp_object', 'id': 'edge'})
        act(ctx, 'cut:fresh_tissue|stone_edged', {'verb': 'cut_tissue', 'tool': 'edge'})
        cap.learn_from_tick(ctx, [])
    assert all(e.get('gain_sum_basal', 0.0) == 0 for e in empty.agent['cognition']['transition_memory']['edges'])
    first = empty.agent['cognition']['transition_memory']['edges'][0]['before']
    assert tm.action_values(empty.agent['cognition'], first, 2000)['grasp:stone_edged|none'] < 0


def test_repeated_access_and_capture_routes_share_one_real_food_budget():
    sc = scene()
    ctx = context(sc)
    ctx.performed = [('strike:animal_grazer|none', {'capture': True, 'fresh_before_kg': 0.0}),
                     ('cut:fresh_tissue|stone_edged', {'access_bonus_kg': 1.0}),
                     ('cut:fresh_tissue|stone_edged', {'access_bonus_kg': 1.0})]
    intake = [{'kind': 'fresh_tissue', 'kg': 1.0, 'kcal': 4320.0,
               'refused_kcal': 320.0, 'handling_kcal': 40.0}]
    gains = cap._sequence_food_gains(ctx, intake, 0.25)
    assert sum(gains) == pytest.approx(3960.0)
    assert gains[1] > 0 and gains[2] == 0  # the last cut did not enable more intake
    intake[0]['refused_kcal'] = 4320.0
    assert cap._sequence_food_gains(ctx, intake, 0.25) == [0.0, 0.0, 0.0]
    # An edge adds no benefit when ordinary hand access already covers the meal.
    ctx.performed = [('cut:fresh_tissue|stone_edged', {'access_bonus_kg': 1.0})]
    intake[0].update(kg=0.1, refused_kcal=0.0)
    assert cap._sequence_food_gains(ctx, intake, 0.25) == [0.0]


def test_a_context_cannot_credit_the_same_meal_twice():
    sc = scene()
    reset_food_trial(sc)
    ctx = context(sc)
    act(ctx, 'grasp:stone_edged|none', {'verb': 'grasp_object', 'id': 'edge'})
    act(ctx, 'cut:fresh_tissue|stone_edged', {'verb': 'cut_tissue', 'tool': 'edge'})
    intake = forage_at_cell(sc.agent, ctx.pcell, ctx.ccell, ctx.profile,
                            sc.agent['cognition']['food_values'], (), ctx.access_bonus)
    cap.learn_from_tick(ctx, intake)
    memory = deepcopy(sc.agent['cognition'])
    cap.learn_from_tick(ctx, intake)
    assert sc.agent['cognition'] == memory


def test_failures_and_costs_extinguish_a_previously_useful_prediction():
    cognition = {}
    before, after = {'acts': ['a']}, {'acts': []}
    for i in range(3):
        eid = tm.record(cognition, before, 'a', after, 20, 0, i, model=tm.VALUED_MODEL)
        tm.credit(cognition, eid, 0.2)
    assert tm.action_values(cognition, before, 100)['a'] < 0  # uncertainty plus real cost
    for i in range(3, 9):
        eid = tm.record(cognition, before, 'a', after, 20, 0, i, model=tm.VALUED_MODEL)
        tm.credit(cognition, eid, 1.0)
    assert tm.action_values(cognition, before, 100)['a'] > 0
    for i in range(9, 60):
        tm.record(cognition, before, 'a', before, 20, 0.1, i, model=tm.VALUED_MODEL)
    assert tm.action_values(cognition, before, 100)['a'] < 0


def test_three_action_search_terminates_and_requires_newly_enabled_continuation():
    cognition = {}
    states = [{'acts': ['a']}, {'acts': ['b']}, {'acts': ['c']}, {'acts': []}]
    for _ in range(5):
        for i, act_key in enumerate(['a', 'b', 'c']):
            eid = tm.record(cognition, states[i], act_key, states[i + 1], 1, 0, 1, model=tm.VALUED_MODEL)
            if act_key == 'c':
                tm.credit(cognition, eid, 1.0)
    assert tm.action_values(cognition, states[0], 100, depth=2)['a'] < 0
    assert tm.action_values(cognition, states[0], 100, depth=3)['a'] > 0
    assert tm.action_values(cognition, states[0], 100, depth=99) == tm.action_values(cognition, states[0], 100, depth=3)


def test_urgent_reserves_prevent_speculative_choice_and_absent_material_is_not_offered():
    sc = scene()
    ctx = train_food(sc)
    options = cap.enumerate_affordances(ctx)
    # The option remains visible but the plan cannot spend near-lethal reserves.
    sc.agent['energy'] = 1000.0
    ctx.draw = lambda *args: 0.99
    assert cap.choose(ctx, options, 0, True) is None
    assert not sc.humans['capacity_stats'].get('sequence_choices')
    sc.agent['energy'] = 10000.0
    sc.agent['body_water_kg'] = 22.0  # one kg above lethal floor, less than two days
    assert cap.choose(ctx, options, 0, True) is None
    sc.agent['body_water_kg'] = 42.0
    sc.humans['objects'] = []
    assert not any(k.startswith('grasp:') for k, _ in cap.enumerate_affordances(ctx))
    picked = cap.choose(ctx, cap.enumerate_affordances(ctx), 0, True)
    assert picked is None or not picked[0].startswith('grasp:')


def surface(sc):
    strand = mo.make_fiber('plant', {'C': 0.03}, 0.5, 0.5, 'strand')
    return {'id': 'surface', 'material': 'surface', 'strands': [strand],
            'area_m2': 0.5, 'cohesion': 0.9, 'x': 0, 'y': 0, 'holder': None, 'worn': False}


def test_worn_benefit_values_grasp_then_wear_and_does_not_recredit_passive_days():
    sc = scene()
    for day in range(1, 9):
        sc.set_agent(0, 0, energy=10000.0)
        sc.humans['objects'] = [surface(sc)]
        ctx = context(sc, day, temperature=0.0)
        act(ctx, 'grasp:surface|none', {'verb': 'grasp_object', 'id': 'surface'})
        act(ctx, 'wear:surface|held', {'verb': 'wear', 'id': 'surface'})
        cap.learn_from_tick(ctx, [])
        _apply_physiology(sc.agent, ctx.wcell, False, ctx.profile, ctx.pcell,
                          insulation_c=cap.insulation_c(sc.humans, sc.agent['id']))
        saving = sc.agent.pop('insulation_saving_kcal')
        assert saving > 0
        cap.credit_transition_heat(ctx, saving, 0)
        before = deepcopy(sc.agent['cognition']['transition_memory'])
        cap.credit_transition_heat(ctx, saving, 0)
        assert sc.agent['cognition']['transition_memory'] == before
    first = next(e for e in sc.agent['cognition']['transition_memory']['edges'] if e['act'] == 'grasp:surface|none')['before']
    assert tm.action_values(sc.agent['cognition'], first, 2000)['grasp:surface|none'] > 0
    idle = context(sc, 9, temperature=0.0)
    cap.credit_transition_heat(idle, 50, 0)
    assert sc.agent['cognition']['transition_memory'] == before


def test_arrangement_readout_is_local_position_sensitive_and_physically_read_only():
    sc = scene()
    pc = sc._p(0, 0)
    pc['arranged_material_elements_kg'] = {'C': 30.0}
    pc['arrangement_geometry'] = {'span_m': 1.5, 'height_m': 1.2,
                                  'surface_area_m2': 2.0, 'density': 1.0, 'orientation_deg': 0.0}
    ctx = context(sc, temperature=0.0)
    before = deepcopy(sc.agent)
    measured, unmeasured = deepcopy(before), deepcopy(before)
    _apply_physiology(measured, ctx.wcell, False, ctx.profile, pc, record_arrangement_benefit=True)
    _apply_physiology(unmeasured, ctx.wcell, False, ctx.profile, pc)
    saving = measured.pop('arrangement_saving_kcal')
    assert saving > 0 and measured == unmeasured
    outside = deepcopy(before)
    outside['subcell_offset_m'] = [3, 0]
    _apply_physiology(outside, ctx.wcell, False, ctx.profile, pc, record_arrangement_benefit=True)
    assert outside.pop('arrangement_saving_kcal') == 0
    pc['arranged_material_elements_kg'] = {'C': 0.0}
    gone = deepcopy(before)
    _apply_physiology(gone, ctx.wcell, False, ctx.profile, pc, record_arrangement_benefit=True)
    assert gone.pop('arrangement_saving_kcal') == 0


def test_arrangement_credit_requires_own_real_change_and_never_rewards_passive_occupancy():
    sc = scene()
    sc.set_pool(0, 0, 'woody_elements_kg', 10.0)
    ctx = context(sc, temperature=0.0)
    act(ctx, 'apply_force:woody|none', {'verb': 'pool', 'sequence': ('apply_force',)})
    act(ctx, 'arrange:loose_wood|none', {'verb': 'pool', 'sequence': ('arrange',)})
    cap.learn_from_tick(ctx, [])
    _apply_physiology(sc.agent, dict(ctx.wcell, temperature=0.0), False, ctx.profile,
                      ctx.pcell, record_arrangement_benefit=True)
    saving = sc.agent.pop('arrangement_saving_kcal')
    assert saving > 0
    cap.credit_transition_heat(ctx, 0, saving)
    edges = sc.agent['cognition']['transition_memory']['edges']
    assert edges[0].get('gain_sum_basal', 0) == 0  # precursor has no invented direct payoff
    assert edges[1]['gain_sum_basal'] == pytest.approx(saving / 2000, abs=5e-11)
    memory = deepcopy(sc.agent['cognition']['transition_memory'])
    cap.credit_transition_heat(context(sc, 2), 0, 100)
    assert sc.agent['cognition']['transition_memory'] == memory


def test_valued_model_rejects_legacy_unmeasured_energy_credit():
    sc = scene()
    with pytest.raises(ValueError, match='energy accounting'):
        replace(sc.config, agentus_transition_model=tm.VALUED_MODEL,
                child_energy_store='unscaled-eating-legacy')
    assert GenesisConfig().agentus_transition_model == 'none'


def test_unscripted_trials_discover_a_useful_chain_and_repeat_it():
    sc = scene()
    assert sc.agent['cognition']['affordance_values'] == {}
    assert 'transition_memory' not in sc.agent['cognition']
    first_sequence_trial = None
    completed_chains = 0
    for day in range(1, 301):
        reset_food_trial(sc)
        ctx = context(sc, day)
        ctx = cap.run_interactions(sc.humans, sc.agent, ctx.profile, ctx.pcell, ctx.ccell,
                                   ctx.lithic_cells, ctx.wcell, sc.consumers, day, True)
        keys = [key for key, _ in ctx.performed]
        if ('grasp:stone_edged|none' in keys and 'cut:fresh_tissue|stone_edged' in keys):
            completed_chains += 1
            if first_sequence_trial is None:
                first_sequence_trial = day
        assert len(keys) <= cap.MAX_INTERACTIONS_PER_TICK
        intake = forage_at_cell(sc.agent, ctx.pcell, ctx.ccell, ctx.profile,
                                sc.agent['cognition']['food_values'], (), ctx.access_bonus)
        cap.learn_from_tick(ctx, intake)
    stats = sc.humans['capacity_stats']
    assert first_sequence_trial is not None and completed_chains >= 5
    assert stats['sequence_exploration']['grasp:stone_edged|none'] > 0
    assert stats['sequence_choices']['grasp:stone_edged|none'] > 0
    assert sc.agent['cognition']['affordance_values']['grasp:stone_edged|none']['v'] < 0
    # The preparatory act is repeated for its learned continuation, rather than
    # because a temporal trace injected a positive individual action value.


def test_failed_wear_and_changed_weather_do_not_inherit_a_thermal_payoff():
    sc = scene()
    worn = surface(sc)
    worn.update(holder=sc.agent['id'], worn=True)
    sc.humans['objects'] = [worn]
    ctx = context(sc, temperature=0.0)
    out = act(ctx, 'wear:surface|held', {'verb': 'wear', 'id': 'surface'})
    assert not out['wear_changed']
    cap.credit_transition_heat(ctx, 50.0, 0)
    assert sc.agent['cognition']['transition_memory']['edges'][0].get('gain_sum_basal', 0) == 0
    learned = scene()
    trained = train_food(learned)
    assert tm.action_values(learned.agent['cognition'], cap._transition_perception(trained), 2000)['grasp:stone_edged|none'] > 0
    changed = context(learned, temperature=40.0)
    assert not tm.action_values(learned.agent['cognition'], cap._transition_perception(changed), 2000)


def test_a_minor_change_cannot_claim_the_benefit_of_preexisting_cover():
    sc = scene()
    pc = sc._p(0, 0)
    pc['arranged_material_elements_kg'] = {'C': 30.0}
    pc['loose_material_elements_kg'] = {'C': 0.25}
    pc['arrangement_geometry'] = {'span_m': 1.5, 'height_m': 1.2,
                                  'surface_area_m2': 2.0, 'density': 1.0, 'orientation_deg': 0.0}
    ctx = context(sc, temperature=0.0)
    act(ctx, 'arrange:loose_wood|none', {'verb': 'pool', 'sequence': ('arrange',)})
    cap.learn_from_tick(ctx, [])
    _apply_physiology(sc.agent, ctx.wcell, False, ctx.profile, ctx.pcell,
                      record_arrangement_benefit=True, arrangement_reference=ctx.arrangement_before)
    saving = sc.agent.pop('arrangement_saving_kcal')
    assert saving == 0.0  # protection was already at the same bounded effectiveness
    cap.credit_transition_heat(ctx, 0, saving)
    assert sc.agent['cognition']['transition_memory']['edges'][0].get('gain_sum_basal', 0) == 0


def test_a_new_tiny_surface_cannot_claim_preexisting_worn_protection():
    sc = scene()
    existing = surface(sc)
    existing.update(id='existing', holder=sc.agent['id'], worn=True)
    tiny = surface(sc)
    tiny.update(id='tiny', holder=sc.agent['id'], area_m2=0.0001)
    sc.humans['objects'] = [existing, tiny]
    ctx = context(sc, temperature=0.0)
    act(ctx, 'wear:surface|held', {'verb': 'wear', 'id': 'tiny'})
    _apply_physiology(sc.agent, ctx.wcell, False, ctx.profile, ctx.pcell,
                      insulation_c=cap.insulation_c(sc.humans, sc.agent['id']),
                      record_arrangement_benefit=True,
                      arrangement_reference=ctx.arrangement_before,
                      insulation_reference_c=ctx.insulation_before)
    saving = sc.agent.pop('insulation_saving_kcal')
    assert 0 < saving < 0.01
    assert sc.agent.pop('arrangement_saving_kcal') == 0
    cap.credit_transition_heat(ctx, saving, 0)
    assert sc.agent['cognition']['transition_memory']['edges'][0]['gain_sum_basal'] < 0.01 / 2000


def test_joint_thermal_credit_cannot_double_count_a_capped_energy_debit():
    sc = scene()
    ctx = context(sc, temperature=-35.0)
    pc = ctx.pcell
    pc['arranged_material_elements_kg'] = {'C': 30.0}
    pc['arrangement_geometry'] = {'span_m': 1.5, 'height_m': 1.2,
                                  'surface_area_m2': 2.0, 'density': 1.0, 'orientation_deg': 0.0}
    old, measured = deepcopy(sc.agent), deepcopy(sc.agent)
    _apply_physiology(old, ctx.wcell, False, ctx.profile, {})
    _apply_physiology(measured, ctx.wcell, False, ctx.profile, pc,
                      insulation_c=7.2, record_arrangement_benefit=True,
                      arrangement_reference=ctx.arrangement_before, insulation_reference_c=0.0)
    worn_gain = measured.pop('insulation_saving_kcal')
    cover_gain = measured.pop('arrangement_saving_kcal')
    assert worn_gain > 0 and cover_gain > 0
    assert worn_gain + cover_gain <= measured['energy'] - old['energy'] + 1e-9
