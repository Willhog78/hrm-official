"""Observe actual exclusions/draws without changing chooser or physical state."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from hrm_genesis import GenesisSimulation
from hrm_genesis.human import interactions as cap, transitions as tm
from qualification.genesis.discovery import config_for
from qualification.genesis.frontier_exclusions import Exclusions, physical_differences


KEY = 'work:material|held'
OPTION = (KEY, {'verb': 'test'})


def context(monkeypatch, attempts=1, enabled=True, draw=1):
    state = {'acts': [KEY], 'held': [['material', 1]], 'body': [3, 3, 1, 0], 'weather': [0]}
    after = dict(state, acts=[KEY, 'next'] if enabled else [KEY])
    cognition = {'affordance_values': {KEY: {'n': 1, 'v': -.1}}}
    for i in range(attempts):
        tm.record(cognition, state, KEY, after, 10, 0, i, model=tm.PROCEDURAL_MODEL)
    ctx = SimpleNamespace(humans={'transition_model': tm.PROCEDURAL_MODEL,
                                 'frontier_state_model': 'procedural-frontier-v1'},
                          human={'energy': 400, 'body_water_kg': 10, 'cognition': cognition},
                          profile={'basal_energy_kcal_per_tick': 100, 'water_loss_per_tick_kg': 1,
                                   'water_capacity_kg': 10, 'min_water_fraction': .5},
                          wcell={}, stats=cap.empty_stats(),
                          draw=lambda name, step: draw if name == 'sequence-frontier' else 1)
    monkeypatch.setattr(cap, '_transition_perception', lambda _: state)
    return ctx, state


@pytest.mark.parametrize('case,status', [('missing', 'no_retained_attempt'),
    ('weather', 'physical_state_mismatch'), ('enabled', 'no_enabled_successor'),
    ('budget', 'attempt_budget_exhausted'), ('draw', 'candidate_trial_declined'),
    ('selected', 'candidate_selected'), ('reserve', 'reserve_blocked'),
    ('untried', 'untried_single_action')])
def test_live_exclusions_partition_offered_option_and_preserve_draw(monkeypatch, case, status):
    ctx, state = context(monkeypatch, attempts=8 if case == 'budget' else 1,
                         enabled=case != 'enabled', draw=0 if case == 'selected' else 1)
    if case == 'missing':
        ctx.human['cognition']['transition_memory']['edges'] = []
    elif case == 'weather':
        state['weather'] = [1]
    elif case == 'reserve':
        ctx.human['energy'] = 199
    elif case == 'untried':
        ctx.human['cognition']['affordance_values'] = {}
    draw_before = ctx.draw
    original = cap.choose
    observer = Exclusions()
    observer.install()
    try:
        picked = cap.choose(ctx, [OPTION], 0, False)
    finally:
        observer.uninstall()
    assert ctx.draw is draw_before and cap.choose is original
    assert observer.options[KEY] == {status: 1}
    assert observer.consistency_errors == 0
    assert (picked == OPTION) == (case == 'selected')
    if case == 'weather':
        assert observer.closest_mismatch[KEY] == {'weather': 1}


def test_preemption_and_empty_options_are_not_trial_failures(monkeypatch):
    ctx, _ = context(monkeypatch)
    observer = Exclusions()
    observer.inspect(ctx, [OPTION], None, 'ordinary_novelty', None)
    assert observer.options[KEY] == {'preempted:ordinary_novelty': 1}
    observer.inspect(ctx, [], None, None, None)
    assert observer.calls == {'no_options': 1}


def test_closest_difference_retains_all_physical_fields_but_ignores_body_drift():
    before = {'body': [4, 4, 0, 0], 'weather': [1], 'held': [['strand', 1]]}
    current = dict(before, body=[2, 3, 1, 0])
    assert physical_differences(before, current) == []
    current['body'][3] = 1
    current['weather'] = [2]
    assert physical_differences(before, current) == ['injury', 'weather']


def test_full_world_matches_plain_snapshot_and_restores_inherited_draw():
    config = replace(config_for('agentus-demography-a', True), agentus_local_work_enabled=True,
                     agentus_surface_work_enabled=True, agentus_frontier_state_enabled=True)
    observed = GenesisSimulation(config)
    observer = Exclusions()
    original = cap.choose
    observer.install()
    try:
        observed.run(20)
    finally:
        observer.uninstall()
    plain = GenesisSimulation(config)
    plain.run(20)
    assert cap.choose is original
    assert observed.snapshot() == plain.snapshot()
    assert observed.ledger.digest() == plain.ledger.digest()
    assert observed.ledger.verify_chain()
    assert observer.consistency_errors == 0
    assert observer.calls['choose_calls'] > 0


def test_draw_override_restores_even_when_live_chooser_raises(monkeypatch):
    ctx, _ = context(monkeypatch)
    def raising(*args):
        raise RuntimeError('diagnostic exception')
    monkeypatch.setattr(cap, 'choose', raising)
    original_draw = ctx.draw
    observer = Exclusions()
    observer.install()
    try:
        with pytest.raises(RuntimeError, match='diagnostic exception'):
            cap.choose(ctx, [OPTION], 0, False)
    finally:
        observer.uninstall()
    assert ctx.draw is original_draw and cap.choose is raising
