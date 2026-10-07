"""MICRO: learning. Positive expectations only from real benefit."""

from __future__ import annotations

import pytest
from _scenario import Scenario, el
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.diet import forage_at_cell, innate_food_prior


def _ctx(sc: Scenario, epoch: int = 3) -> cap.Context:
    xy = sc.xy
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == xy)
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(*xy),
                       sc.matter["lithic_cells"], {"precipitation": 0.0}, sc.consumers, epoch)


def test_direct_experience_cutting_meat_with_an_edge_becomes_valued():
    sc = Scenario(capacities=True)
    sc.set_agent(0, 0, energy=10000.0)
    sc.agent["cognition"]["food_values"]["fresh_tissue"] = 4000.0
    sc.set_fresh_tissue(0, 0, 5.0)
    flake = {"id": "flake", "material": "stone", "fragment": {"id": "flake", "lith": "siliceous_fine", "m": 0.1, "s": 0.85, "e": 3.0},
             "x": 0, "y": 0, "holder": sc.agent["id"], "worn": False}
    sc.humans["objects"].append(flake)
    ctx = _ctx(sc)
    out = cap.execute(ctx, "cut:fresh_tissue|stone_edged", {"verb": "cut_tissue", "tool": "flake"})
    ctx.performed.append(("cut:fresh_tissue|stone_edged", out))
    intake = forage_at_cell(sc.agent, ctx.pcell, ctx.ccell, ctx.profile, sc.agent["cognition"]["food_values"], (), ctx.access_bonus)
    cap.learn_from_tick(ctx, intake)
    assert sc.agent["cognition"]["affordance_values"]["cut:fresh_tissue|stone_edged"]["v"] > 0.0


def test_delayed_credit_reaches_the_preparation_recorded_in_the_tool():
    sc = Scenario(capacities=True)
    sc.add_stone(0, 0, "flake", lith="siliceous_fine", m=0.1, s=0.85, e=3.0)
    ctx = _ctx(sc, 1)
    cap.execute(ctx, "grasp:stone_edged|none", {"verb": "grasp_natural", "id": "flake"})
    sc.agent["cognition"]["affordance_values"] = {"grasp:stone_edged|none": {"n": 1, "v": -0.004}}
    # Many days later, the same flake pays off.
    sc.agent["cognition"]["food_values"]["fresh_tissue"] = 4000.0
    sc.set_fresh_tissue(0, 0, 5.0)
    ctx = _ctx(sc, 50)
    out = cap.execute(ctx, "cut:fresh_tissue|stone_edged", {"verb": "cut_tissue", "tool": "flake"})
    ctx.performed.append(("cut:fresh_tissue|stone_edged", out))
    intake = forage_at_cell(sc.agent, ctx.pcell, ctx.ccell, ctx.profile, sc.agent["cognition"]["food_values"], (), ctx.access_bonus)
    cap.learn_from_tick(ctx, intake)
    assert sc.agent["cognition"]["affordance_values"]["grasp:stone_edged|none"]["v"] > 0.0


def test_observed_success_transmits_but_observed_failure_does_not():
    sc = Scenario(capacities=True)
    watcher = sc.add_agent("watcher", 0, 0)
    ctx = _ctx(sc)
    cap.observe_outcome(ctx, "cut:fresh_tissue|stone_edged", 0.3)
    cap.observe_outcome(ctx, "strike:animal_grazer|none", -0.2)
    values = watcher["cognition"]["affordance_values"]
    assert values["cut:fresh_tissue|stone_edged"]["v"] > 0.0 and "strike:animal_grazer|none" not in values


def test_failed_capture_is_learned_as_negative():
    sc = Scenario(capacities=True)
    sc.add_animal("browser-1", "browser", 0, 0, energy=80.0)  # well fed, alert: hard to catch
    for epoch in range(200):
        ctx = _ctx(sc, epoch)
        if not any(a["id"] == "browser-1" and (a["x"], a["y"]) == (0, 0) for a in sc.consumers["animals"]):
            break
        out = cap.execute(ctx, "strike:animal_browser|none", {"verb": "capture", "tool": None, "animal": "browser-1"})
        if not out.get("capture"):
            ctx.performed.append(("strike:animal_browser|none", out))
            cap.learn_from_tick(ctx, [])
            break
    assert sc.agent["cognition"]["affordance_values"]["strike:animal_browser|none"]["v"] < 0.0


def _barren_but_rich_in_materials(sc: Scenario) -> None:
    for x in range(3):
        sc.set_water(x, 0, 50000.0)
        sc.set_pool(x, 0, "plant_elements_kg", 5000.0)
        sc.set_pool(x, 0, "woody_elements_kg", 500.0)
        sc.add_stone(x, 0, f"s{x}a", lith="siliceous_fine", m=1.0)
        sc.add_stone(x, 0, f"s{x}b", lith="basaltic", m=0.8)


def test_a_world_without_payoffs_teaches_no_positive_habits():
    """400 days of the real choose/execute/learn loop on stones, wood and
    plants with no meat and no cold: nothing pays, so nothing may end up
    valued or repeated. The agent stays rested so movement fatigue (see the
    next test) cannot hide the question."""
    sc = Scenario(capacities=True, width=3)
    sc.set_agent(1, 0)
    _barren_but_rich_in_materials(sc)
    for epoch in range(1, 401):
        sc.agent["fatigue"] = 0.0
        ctx = _ctx(sc, epoch)
        ctx = cap.run_interactions(sc.humans, sc.agent, ctx.profile, ctx.pcell, ctx.ccell, ctx.lithic_cells,
                                   ctx.wcell, sc.consumers, epoch, hungry=False)
        cap.learn_from_tick(ctx, [])
    counts = sc.humans["capacity_stats"]["interaction_counts"]
    values = sc.agent["cognition"]["affordance_values"]
    assert sum(counts.values()) >= 5, f"too little exploration to test: {counts}"
    positive = {k: v for k, v in values.items() if float(v["v"]) > 0.0}
    assert not positive, f"habits formed without any benefit: {positive}"
    assert not sc.humans["capacity_stats"].get("exploit_by_key"), "repeated an action that never paid"


def test_a_sated_agent_stays_rested_enough_to_explore():
    sc = Scenario(capacities=True, width=3)
    sc.set_agent(1, 0)
    _barren_but_rich_in_materials(sc)
    sc.step(150)
    assert float(sc.agent["fatigue"]) <= 0.8
    assert sum(sc.humans["capacity_stats"]["interaction_counts"].values()) > 0


def test_daily_walking_reaches_a_steady_fatigue_well_below_the_block():
    from hrm_genesis.human.biology import _apply_physiology
    sc = Scenario()
    a = sc.agent
    for _ in range(200):
        _apply_physiology(a, sc.world["cells"][0], True, sc.profile, sleep_recovery=True)
    assert 0.2 < a["fatigue"] < 0.3  # 0.08 x 0.75 / 0.25 = 0.24


def test_pre_g10_6_fatigue_saturation_is_reproduced_with_integrity_off():
    sc = Scenario(capacities=True, width=3, integrity=False)
    sc.set_agent(1, 0)
    _barren_but_rich_in_materials(sc)
    sc.step(150)
    assert float(sc.agent["fatigue"]) > 0.8
