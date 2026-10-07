"""MICRO: following (G10.7a step 4). Learned from experience only.

A hungry agent with nowhere known to go may move to where a visible individual
is now. Whether that is worth doing is learned from its own outcomes compared
with its own exploring alone. No coordinates beyond what is in view, no
inferred destination, no leader label, nothing written to the one followed.
"""

from __future__ import annotations

from _scenario import Scenario
from hrm_genesis.human import planning
from hrm_genesis.human.diet import innate_food_prior


def _hungry_scene(width: int = 5, **kw) -> Scenario:
    sc = Scenario(capacities=True, width=width, **kw)
    sc.set_agent(2, 0, energy=0.4 * float(sc.profile["energy_capacity_kcal"]))
    sc.agent["cognition"]["food_values"] = innate_food_prior(sc.profile)
    for x in range(width):
        sc.set_water(x, 0, 50000.0)
    return sc


def _peer(sc: Scenario, x: int, aid: str = "human-g00000777"):
    p = sc.add_agent(aid, x, 0)
    p["energy"] = float(sc.profile["energy_capacity_kcal"])  # sated: it stays put unless it has reason
    return p


def test_a_valued_individual_in_view_is_followed():
    sc = _hungry_scene()
    peer = _peer(sc, 3)
    sc.agent["cognition"]["follow_values"] = {peer["id"]: 0.4}
    sc.step()
    assert sc.xy == (3, 0)


def test_an_individual_whose_company_did_not_pay_is_not_followed():
    sc = _hungry_scene()
    peer = _peer(sc, 3)
    sc.agent["cognition"]["follow_values"] = {peer["id"]: -0.4}
    sc.agent["cognition"]["memory"]["episodes"] = [{"epoch": 0, "origin": [3, 0], "reward": 0.0}]  # explore elsewhere
    sc.step()
    assert sc.xy != (3, 0)


def test_individuals_out_of_view_cannot_be_followed():
    sc = _hungry_scene()
    peer = _peer(sc, 4)  # two cells away: not perceived
    sc.agent["cognition"]["follow_values"] = {peer["id"]: 5.0}
    perception_seen = {}
    original = planning._follow_target

    def spy(perception, cognition):
        perception_seen["peers"] = list(perception["visible_peers"])
        return original(perception, cognition)

    planning._follow_target = spy
    try:
        sc.step()
    finally:
        planning._follow_target = original
    assert all(pid != peer["id"] for pid, _, _ in perception_seen["peers"])


def test_untried_individuals_are_sometimes_tried():
    perception = {"visible_peers": [("p", 3, 0)], "follow_pick": 0.0}
    tried = sum(planning._follow_target(dict(perception, follow_draw=d / 100), {}) is not None for d in range(100))
    assert tried == int(planning.FOLLOW_TRIAL * 100)


def test_following_to_an_empty_place_is_learned_as_no_better_than_exploring():
    sc = _hungry_scene()
    peer = _peer(sc, 3)
    sc.agent["cognition"]["follow_values"] = {peer["id"]: 0.01}
    sc.agent["cognition"]["explore_baseline"] = 0.0
    sc.step()
    assert sc.xy == (3, 0)
    assert sc.agent["cognition"]["follow_values"][peer["id"]] <= 0.01
    assert sc.humans["capacity_stats"]["follow_outcomes"] == {"not_better": 1}


def test_value_is_relative_to_the_agents_own_exploring():
    from hrm_genesis.human import interactions as cap
    humans = {"humans": [], "capacity_stats": {}}
    agent = {"id": "a", "cognition": {"explore_baseline": 0.6}}
    cap.learn_following(humans, agent, {"chosen_by": ("follow", "p"), "forage_need_kg": 1.0}, 0.4)
    assert agent["cognition"]["follow_values"]["p"] < 0.0  # worse than going alone
    agent2 = {"id": "b", "cognition": {"explore_baseline": 0.1}}
    cap.learn_following(humans, agent2, {"chosen_by": ("follow", "p"), "forage_need_kg": 1.0}, 0.4)
    assert agent2["cognition"]["follow_values"]["p"] > 0.0


def test_nothing_is_written_to_the_individual_followed():
    sc = _hungry_scene()
    peer = _peer(sc, 3)
    before = {k: v for k, v in peer["cognition"].items() if k != "memory"}
    sc.agent["cognition"]["follow_values"] = {peer["id"]: 0.4}
    sc.step()
    after = next(h for h in sc.humans["humans"] if h["id"] == peer["id"])
    assert "follow_values" not in after["cognition"] and "leader" not in str(after)
    assert set(after["cognition"]) == set(before) | {"memory"}


def test_drives_with_somewhere_known_to_go_are_not_overridden():
    sc = _hungry_scene()
    peer = _peer(sc, 3)
    sc.set_pool(1, 0, "plant_elements_kg", 500.0)  # visible food the other way
    sc.agent["cognition"]["follow_values"] = {peer["id"]: 5.0}
    sc.step()
    assert sc.xy == (1, 0)


def test_following_off_reproduces_step_3():
    a, b = _hungry_scene(following=False), _hungry_scene(following=False)
    _peer(a, 3)
    a.agent["cognition"]["follow_values"] = {"human-g00000777": 5.0}
    _peer(b, 3)
    a.step(); b.step()
    assert a.xy == b.xy
