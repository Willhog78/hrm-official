"""G10.4: delayed benefit reaches preparation; outcomes can be observed."""

from __future__ import annotations

from copy import deepcopy

from hrm_genesis.human import interactions as cap
from hrm_genesis.human.biology import _apply_physiology
from hrm_genesis.human.calibration import reference_adult_profile
from hrm_genesis.matter import objects as mo

FRACTIONS = {"C": 0.86, "N": 0.08, "K": 0.025, "P": 0.012, "Mg": 0.013, "S": 0.01}


def _el(kg):
    return {s: kg * f for s, f in FRACTIONS.items()}


def _profile():
    p = dict(reference_adult_profile(365))
    p.update(development_scale=1.0, target_dry_mass_kg=p["seed_dry_mass_kg"])
    return p


def _agent(aid="a", x=0, y=0):
    return {"id": aid, "x": x, "y": y, "energy": 10000.0, "body_elements_kg": _el(20.0), "body_water_kg": 42.0,
            "fatigue": 0.0, "injury": 0.0, "held_material_elements_kg": _el(0.0),
            "cognition": {"memory": {"episodes": [], "locations": {}}, "food_values": {}, "affordance_values": {}, "trace": []}}


def _pcell(**kw):
    cell = {k: _el(kw.get(k.split("_")[0], 0.0)) for k in
            ("plant_elements_kg", "seed_elements_kg", "woody_elements_kg", "loose_material_elements_kg",
             "arranged_material_elements_kg", "detritus_elements_kg")}
    cell.update(x=0, y=0, fire_intensity=0.0)
    return cell


def _humans(*agents):
    return {"humans": list(agents), "objects": [], "next_object_ordinal": 0, "capacity_stats": cap.empty_stats()}


def _ctx(humans, agent, pcell=None, lithic=None, epoch=3):
    consumers = {"width": 3, "height": 3, "animals": [], "carcass_cells": [], "cumulative_deaths_by_cause": {}}
    ccell = {"x": 0, "y": 0, "elements_kg": _el(0.0), "fresh_elements_kg": _el(0.0), "water_kg": 0.0}
    return cap.Context(humans, agent, _profile(), pcell or _pcell(), ccell, lithic or {}, {"precipitation": 0.0}, consumers, epoch)


def test_objects_carry_the_history_of_their_making():
    humans = _humans(_agent())
    agent = humans["humans"][0]
    lithic = {"0,0": [{"id": "hammer", "lith": "basaltic", "m": 1.0, "s": 0.1, "e": 1.2},
                      {"id": "core", "lith": "siliceous_fine", "m": 0.6, "s": 0.1, "e": 1.0}]}
    ctx = _ctx(humans, agent, lithic=lithic)
    cap.execute(ctx, "grasp:stone_heavy|none", {"verb": "grasp_natural", "id": "hammer"})
    hammer = cap._find(humans, "hammer")
    assert hammer["history"] == ["grasp:stone_heavy|none"]
    cap.execute(ctx, "strike:stone_heavy|stone_heavy", {"verb": "strike_stone", "tool": "hammer", "natural": "core"})
    produced = [o for o in humans["objects"] if o["id"] != "hammer"]
    assert produced, "a fracture must have produced pieces"
    for piece in produced:
        assert piece["history"][-1] == "strike:stone_heavy|stone_heavy"
        assert "grasp:stone_heavy|none" in piece["history"]  # the hammer's preparation


def test_benefit_from_a_tool_credits_preparation_beyond_the_time_window():
    values = {"grasp:stone_small|none": {"n": 1, "v": -0.01}, "strike:x|y": {"n": 1, "v": -0.01}, "recent": {"n": 1, "v": 0.0}}
    history = ["grasp:stone_small|none", "strike:x|y"]
    cap._credit_preparation(values, ["recent"], history, gain_basal=1.0)
    assert values["strike:x|y"]["v"] > 0.0 and values["grasp:stone_small|none"]["v"] > 0.0
    assert values["recent"]["v"] > 0.0


def test_worn_material_saves_cold_stress_and_reinforces_its_making():
    profile = {"calibrated": True, "water_capacity_kg": 42.0}
    bare, worn = _agent(), _agent()
    cold = {"temperature": -15.0, "terrain_cover": 0.0}
    _apply_physiology(bare, cold, moved=False, profile=profile)
    _apply_physiology(worn, cold, moved=False, profile=profile, insulation_c=6.0)
    assert worn["energy"] > bare["energy"]
    saving = worn.pop("insulation_saving_kcal")
    assert abs(saving - (worn["energy"] - bare["energy"])) < 1e-6

    humans = _humans(worn)
    worn["cognition"]["affordance_values"] = {"interlace:strands|held": {"n": 1, "v": -0.01}, "wear:surface|held": {"n": 1, "v": -0.002}}
    humans["objects"].append({"id": "mat", "material": "surface", "strands": [], "area_m2": 1.0, "cohesion": 1.0,
                              "x": 0, "y": 0, "holder": "a", "worn": True,
                              "history": ["interlace:strands|held", "wear:surface|held"]})
    # One cold day saves ~60 kcal; the benefit accrues over the days it is worn.
    cap.credit_worn_benefit(humans, worn, saving, _profile())
    assert worn["cognition"]["affordance_values"]["interlace:strands|held"]["v"] < 0.0
    for _ in range(4):
        cap.credit_worn_benefit(humans, worn, saving, _profile())
    values = worn["cognition"]["affordance_values"]
    assert values["interlace:strands|held"]["v"] > 0.0 and values["wear:surface|held"]["v"] > 0.0


def test_success_is_observed_by_agents_sharing_the_cell_only():
    teacher, near, far = _agent("t"), _agent("n"), _agent("f", x=2)
    humans = _humans(teacher, near, far)
    ctx = _ctx(humans, teacher)
    cap.observe_outcome(ctx, "cut:fresh_tissue|stone_edged", reward=0.4)
    assert near["cognition"]["affordance_values"]["cut:fresh_tissue|stone_edged"]["v"] > 0.0
    assert "cut:fresh_tissue|stone_edged" not in far["cognition"]["affordance_values"]
    cap.observe_outcome(ctx, "strike:x|y", reward=-1.0)
    assert "strike:x|y" not in near["cognition"]["affordance_values"]


def test_observed_beneficial_eating_gives_a_cautious_food_prior():
    eater, watcher = _agent("e"), _agent("w")
    humans = _humans(eater, watcher)
    ctx = _ctx(humans, eater)
    cap.observe_food(ctx, [{"kind": "seed", "kg": 1.0, "kcal": 2850.0, "hazard": 0.0, "handling_kcal": 60.0}])
    assert 0.0 < watcher["cognition"]["food_values"]["seed"] < 2850.0
    cap.observe_food(ctx, [{"kind": "decayed_tissue", "kg": 0.1, "kcal": 0.0, "hazard": 0.06, "handling_kcal": 2.0}])
    assert "decayed_tissue" not in watcher["cognition"]["food_values"]


def test_repeated_use_because_it_paid_is_counted():
    humans = _humans(_agent())
    agent = humans["humans"][0]
    agent["cognition"]["affordance_values"] = {"separate:plant_tissue|none": {"n": 2, "v": 0.3}}
    ctx = _ctx(humans, agent, pcell=_pcell(plant=3.0))
    picked = cap.choose(ctx, cap.enumerate_affordances(ctx), 0, hungry=False)
    assert picked[0] == "separate:plant_tissue|none"
    assert ctx.stats["exploit_by_key"]["separate:plant_tissue|none"] == 1
    assert ctx.stats["exploit_agents"]["separate:plant_tissue|none"] == ["a"]
