"""MICRO: stone. Physical encounter, conserved fracture, edges only by rule."""

from __future__ import annotations

from _scenario import Scenario
from hrm_genesis.human import interactions as cap
from hrm_genesis.matter import objects as mo


def _ctx(sc: Scenario, epoch: int = 3) -> cap.Context:
    xy = sc.xy
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == xy)
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(*xy),
                       sc.matter["lithic_cells"], {"precipitation": 0.0}, sc.consumers, epoch)


def _lithic(sc: Scenario) -> float:
    return cap.lithic_inventory_kg(sc.matter, sc.humans)


def test_stone_must_be_encountered_before_pickup():
    sc = Scenario(capacities=True)
    sc.add_stone(1, 0, "far-stone")
    ctx = _ctx(sc)
    assert not any(k.startswith("grasp:stone") for k, _ in cap.enumerate_affordances(ctx))
    out = cap.execute(ctx, "grasp:stone_heavy|none", {"verb": "grasp_natural", "id": "far-stone"})
    assert not sc.humans["objects"] and out["effort_kcal"] > 0.0  # failed attempt still costs
    sc.add_stone(0, 0, "near-stone")
    ctx = _ctx(sc)
    assert any(k.startswith("grasp:stone") for k, _ in cap.enumerate_affordances(ctx))


def test_picked_stone_is_carried_with_the_agent_and_conserved():
    sc = Scenario(capacities=True)
    sc.set_water(0, 0, 50000.0)
    sc.add_stone(0, 0, "s1", m=1.2)
    total = _lithic(sc)
    cap.execute(_ctx(sc), "grasp:stone_heavy|none", {"verb": "grasp_natural", "id": "s1"})
    stone = cap._find(sc.humans, "s1")
    assert stone and stone["holder"] == sc.agent["id"]
    assert abs(_lithic(sc) - total) < 1e-12
    sc.set_pool(1, 0, "plant_elements_kg", 5000.0)
    sc.set_water(1, 0, 50000.0)
    sc.agent["energy"] = 3000.0  # hungry: it will walk to the food
    sc.step()
    assert sc.xy == (1, 0) and (stone := cap._find(sc.humans, "s1"))["x"] == 1, "carried stone stayed behind"


def test_heavier_than_carry_room_is_not_offered():
    sc = Scenario(capacities=True)
    sc.add_stone(0, 0, "boulder", m=25.0)
    assert not any(k.startswith("grasp:stone") for k, _ in cap.enumerate_affordances(_ctx(sc)))


def test_striking_conserves_lithic_mass():
    sc = Scenario(capacities=True)
    sc.add_stone(0, 0, "hammer", lith="basaltic", m=1.0)
    sc.add_stone(0, 0, "core", lith="siliceous_fine", m=0.6)
    total = _lithic(sc)
    ctx = _ctx(sc)
    cap.execute(ctx, "grasp:stone_heavy|none", {"verb": "grasp_natural", "id": "hammer"})
    for i in range(8):
        target = next((f for f in sc.matter["lithic_cells"].get("0,0", [])), None)
        ground = [o for o in sc.humans["objects"] if o["material"] == "stone" and o["holder"] is None]
        spec = {"verb": "strike_stone", "tool": "hammer"}
        spec.update({"natural": target["id"]} if target else {"object": ground[0]["id"]})
        cap.execute(_ctx(sc, i), "strike:x|y", spec)
        assert abs(_lithic(sc) - total) < 1e-9, f"strike {i} changed lithic mass"
    assert ctx.stats.get("fractures", 0) >= 1


def test_sharp_edges_only_arise_where_the_fracture_rules_allow():
    for lith, expect_sharp in (("granitic_coarse", False), ("siliceous_fine", True)):
        sharp = 0
        for i in range(200):
            frag = {"id": f"t{i}", "lith": lith, "m": 1.0, "s": 0.05, "e": 1.2}
            pieces = mo.fracture(frag, mo.stone_props(frag)["fracture_energy_j"] * 1.5,
                                 mo.unit_draw(lith, i, "a"), mo.unit_draw(lith, i, "b"), "f")
            sharp += pieces is not None and pieces[1]["s"] >= 0.4
        assert (sharp > 0) == expect_sharp, f"{lith}: {sharp} sharp flakes"
    weak = {"id": "w", "lith": "siliceous_fine", "m": 1.0, "s": 0.05, "e": 1.2}
    assert mo.fracture(weak, mo.stone_props(weak)["fracture_energy_j"] * 0.99, 0.5, 0.5, "x") is None


def test_blunt_stone_never_gains_cutting_ability_and_edges_wear():
    blunt = {"id": "b", "lith": "granitic_coarse", "m": 0.8, "s": 0.05, "e": 1.0}
    sharp = {"id": "s", "lith": "siliceous_fine", "m": 0.1, "s": 0.8, "e": 3.0}
    history = []
    for _ in range(30):
        history.append(blunt["s"])
        mo.edge_wear(blunt, 0.5)
    assert all(b <= a for a, b in zip(history, history[1:])), "use sharpened a stone"
    assert mo.cutting_capacity(blunt["s"], 6.0, 0.5, 1.0) < 0.06
    s0 = sharp["s"]
    for _ in range(10):
        mo.edge_wear(sharp, 2.0)
    assert sharp["s"] < s0 and mo.cutting_capacity(sharp["s"], 7.0, 0.5, 1.0) < mo.cutting_capacity(s0, 7.0, 0.5, 1.0)
