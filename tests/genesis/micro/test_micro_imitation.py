"""MICRO: imitation (G10.7a step 3). Memory -> trying, nothing more.

A remembered act that was followed by visible consequences makes an agent more
likely to try the same act (same verb, same object classes), but only when it
is physically possible here and now and the agent has never tried it. No value,
reward or recipe is inherited: the world scores the try like any other.
"""

from __future__ import annotations

from _scenario import Scenario
from hrm_genesis.human import interactions as cap

STRIKE = "strike:stone_heavy|stone_heavy"


def _ctx(sc: Scenario, epoch: int = 5) -> cap.Context:
    xy = sc.xy
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == xy)
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(*xy),
                       sc.matter["lithic_cells"], {"precipitation": 0.0}, sc.consumers, epoch)


def _seen(act: str, salience_fields: dict | None = None, actor: str = "elder") -> dict:
    event = {"epoch": 1, "actor": actor, "act": act, "created": [], "eaten_kg": {}, "hurt": False,
             "appeared": [], "transformed": False, "killed": False, "exposed_kg": 0.0}
    event.update(salience_fields or {})
    return event


FLAKE = {"appeared": ["stone_edged"], "transformed": True}  # salience 2


def _stone_world(**kw) -> Scenario:
    sc = Scenario(capacities=True, **kw)
    sc.add_stone(0, 0, "hammer", lith="basaltic", m=0.8)
    sc.add_stone(0, 0, "core", lith="siliceous_fine", m=1.0)
    hammer = {"id": "hammer", "material": "stone", "fragment": sc.matter["lithic_cells"]["0,0"].pop(0),
              "x": 0, "y": 0, "holder": sc.agent["id"], "worn": False}
    sc.humans["objects"].append(hammer)
    return sc


def _tries(sc: Scenario, key: str, epochs: int = 400) -> int:
    n = 0
    for epoch in range(epochs):
        ctx = _ctx(sc, epoch)
        options = cap.enumerate_affordances(ctx)
        picked = cap.choose(ctx, options, 0, hungry=False)
        n += picked is not None and picked[0] == key
    return n


def test_the_strike_is_physically_available_in_this_scene():
    sc = _stone_world()
    assert STRIKE in [k for k, _ in cap.enumerate_affordances(_ctx(sc))]


def test_seeing_a_conspicuous_act_makes_trying_it_likelier():
    plain = _tries(_stone_world(), STRIKE)
    sc = _stone_world()
    sc.agent["cognition"]["witnessed"] = [_seen(STRIKE, FLAKE)]
    seen = _tries(sc, STRIKE)
    assert seen > 2 * max(1, plain), (plain, seen)
    # 0.15 per consequence x 2 = 0.30 of epochs, give or take sampling
    assert 0.2 * 400 < seen < 0.45 * 400


def test_an_act_seen_with_no_visible_consequence_gives_no_reason_to_copy():
    plain = _tries(_stone_world(), STRIKE)
    sc = _stone_world()
    sc.agent["cognition"]["witnessed"] = [_seen(STRIKE)]
    assert _tries(sc, STRIKE) == plain


def test_nothing_is_tried_that_is_not_physically_possible_here():
    sc = Scenario(capacities=True)  # no stones at all
    sc.agent["cognition"]["witnessed"] = [_seen(STRIKE, FLAKE)]
    assert _tries(sc, STRIKE, 100) == 0


def test_imitation_never_writes_a_value_or_inherits_reward():
    sc = _stone_world()
    sc.agent["cognition"]["witnessed"] = [_seen(STRIKE, FLAKE)]
    for epoch in range(200):
        ctx = _ctx(sc, epoch)
        cap.choose(ctx, cap.enumerate_affordances(ctx), 0, hungry=False)
    assert STRIKE not in sc.agent["cognition"]["affordance_values"]


def test_the_world_scores_an_imitated_try_exactly_like_an_unprompted_one():
    """Same act, same draws: the learned value after trying does not depend on
    having seen someone else do it."""
    results = []
    for witnessed in (False, True):
        sc = _stone_world()
        if witnessed:
            sc.agent["cognition"]["witnessed"] = [_seen(STRIKE, FLAKE)]
        ctx = _ctx(sc, 9)
        spec = dict(next(spec for k, spec in cap.enumerate_affordances(ctx) if k == STRIKE))
        if witnessed:
            ctx.imitated[STRIKE] = ["elder"]
        out = cap.execute(ctx, STRIKE, spec)
        ctx.performed.append((STRIKE, out))
        cap.learn_from_tick(ctx, [])
        results.append(sc.agent["cognition"]["affordance_values"][STRIKE]["v"])
    assert results[0] == results[1]


def test_imitated_tries_are_counted_with_their_source_and_outcome():
    sc = _stone_world()
    ctx = _ctx(sc, 9)
    spec = dict(next(spec for k, spec in cap.enumerate_affordances(ctx) if k == STRIKE))
    ctx.imitated[STRIKE] = ["elder"]
    out = cap.execute(ctx, STRIKE, spec)
    ctx.performed.append((STRIKE, out))
    cap.learn_from_tick(ctx, [])
    stats = sc.humans["capacity_stats"]
    assert stats["imitated_from"][STRIKE] == ["elder"]
    assert stats.get("imitation_paid", {}).get(STRIKE, 0) + stats.get("imitation_unpaid", {}).get(STRIKE, 0) == 1


def test_acts_already_tried_are_left_to_own_experience():
    sc = _stone_world()
    sc.agent["cognition"]["witnessed"] = [_seen(STRIKE, FLAKE)]
    sc.agent["cognition"]["affordance_values"] = {STRIKE: {"n": 2, "v": -0.3}}
    assert _tries(sc, STRIKE) == _tries(_stone_world_with_value(-0.3), STRIKE)


def _stone_world_with_value(v: float) -> Scenario:
    sc = _stone_world()
    sc.agent["cognition"]["affordance_values"] = {STRIKE: {"n": 2, "v": v}}
    return sc


def test_imitation_off_reproduces_step_2_5_choices():
    sc_off = _stone_world(imitation=False)
    sc_off.agent["cognition"]["witnessed"] = [_seen(STRIKE, FLAKE)]
    assert _tries(sc_off, STRIKE) == _tries(_stone_world(imitation=False), STRIKE)


def test_options_sharing_a_key_do_not_break_the_choice():
    sc = _stone_world()
    sc.add_stone(0, 0, "core2", lith="siliceous_fine", m=1.0)  # a second target of the same class
    sc.agent["cognition"]["witnessed"] = [_seen(STRIKE, FLAKE)]
    ctx = _ctx(sc)
    options = cap.enumerate_affordances(ctx)
    assert sum(k == STRIKE for k, _ in options) >= 2
    assert _tries(sc, STRIKE, 50) > 0
