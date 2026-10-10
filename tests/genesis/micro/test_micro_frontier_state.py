"""Retry physical enabling experience after bodily drift, with bounded risk."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from hrm_genesis.human import interactions as cap, transitions as tm


KEY = 'work:material|held'
OPTION = (KEY, {'verb': 'test'})


def state(body=None):
    return {'acts': [KEY], 'held': [['material', 1]], 'ground': [], 'worn': [],
            'pools': [1], 'geometry': [0], 'weather': [0], 'position': [0, 0],
            'access': 0, 'body': body or [4, 4, 0, 0]}


def context(monkeypatch, attempts=1, enabled=True):
    before = state()
    after = state()
    if enabled:
        after['acts'].append('next:material|held')
    cognition = {'affordance_values': {KEY: {'v': -.01, 'n': attempts}}}
    for epoch in range(attempts):
        tm.record(cognition, before, KEY, after, 10, 0, epoch, model=tm.PROCEDURAL_MODEL)
    current = state([3, 3, 1, 0])
    ctx = SimpleNamespace(humans={'transition_model': tm.PROCEDURAL_MODEL,
                                 'frontier_state_model': 'procedural-frontier-v1'},
                          human={'energy': 400, 'body_water_kg': 10, 'cognition': cognition},
                          profile={'basal_energy_kcal_per_tick': 100, 'water_loss_per_tick_kg': 1,
                                   'water_capacity_kg': 10, 'min_water_fraction': .5},
                          wcell={}, stats=cap.empty_stats(),
                          draw=lambda name, step: 0 if name.startswith('sequence-frontier') else 1)
    monkeypatch.setattr(cap, '_transition_perception', lambda _: current)
    return ctx, current, after


def test_opt_in_recognizes_enabling_trial_after_body_drift_without_reward(monkeypatch):
    ctx, current, _ = context(monkeypatch)
    before = deepcopy(ctx.human)
    assert cap.choose(ctx, [OPTION], 0, False) == OPTION
    assert ctx.stats['sequence_exploration'][KEY] == 1
    assert ctx.human == before  # no predicted outcome, invented benefit or cost
    del ctx.humans['frontier_state_model']
    assert cap.choose(ctx, [OPTION], 0, False) is None


@pytest.mark.parametrize('field,value', [('held', [['different', 1]]), ('pools', [2]),
    ('geometry', [1]), ('weather', [1]), ('access', 1), ('position', [1, 0]),
    ('acts', []), ('body', [3, 3, 1, 1])])
def test_physical_mismatch_still_rejects_retry(monkeypatch, field, value):
    ctx, current, _ = context(monkeypatch)
    current[field] = value
    assert cap.choose(ctx, [OPTION], 0, False) is None


@pytest.mark.parametrize('field,value', [('energy', 199), ('body_water_kg', 6.9)])
def test_discretionary_reserve_guard_is_still_required(monkeypatch, field, value):
    ctx, _, _ = context(monkeypatch)
    ctx.human[field] = value
    assert cap.choose(ctx, [OPTION], 0, True) is None


def test_no_enabling_experience_no_offered_action_and_trial_probability(monkeypatch):
    ctx, _, _ = context(monkeypatch, enabled=False)
    assert cap.choose(ctx, [OPTION], 0, False) is None
    ctx, _, _ = context(monkeypatch)
    assert cap.choose(ctx, [], 0, False) is None
    ctx.draw = lambda *_: 1
    assert cap.choose(ctx, [OPTION], 0, False) is None


def test_attempt_limit_aggregates_body_variants_instead_of_resetting_budget(monkeypatch):
    ctx, _, after = context(monkeypatch, attempts=4)
    for epoch in range(4, 8):
        tm.record(ctx.human['cognition'], state([2, 3, 1, 0]), KEY, after, 10, 0, epoch,
                  model=tm.PROCEDURAL_MODEL)
    assert cap.choose(ctx, [OPTION], 0, False) is None


def test_promising_successor_matches_body_drift_but_extra_budget_stays_finite(monkeypatch):
    ctx, _, after = context(monkeypatch, attempts=8)
    successor = deepcopy(after)
    successor['body'] = [2, 3, 1, 0]
    edge = tm.record(ctx.human['cognition'], successor, 'next:material|held', state(), 1000, 0, 8,
                     model=tm.PROCEDURAL_MODEL)
    tm.credit(ctx.human['cognition'], edge, .01)
    assert cap.choose(ctx, [OPTION], 0, False) == OPTION
    for epoch in range(9, 17):
        tm.record(ctx.human['cognition'], state(), KEY, after, 10, 0, epoch, model=tm.PROCEDURAL_MODEL)
    assert cap.choose(ctx, [OPTION], 0, False) is None
