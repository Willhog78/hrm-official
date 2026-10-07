"""MICRO: fibers. Extraction needs material here; manipulation conserves mass;
bindings hold, slip or break; pointless repetition costs and is not rewarded."""

from __future__ import annotations

from _scenario import Scenario, el, mass
from hrm_genesis.human import interactions as cap
from hrm_genesis.matter import objects as mo


def _ctx(sc: Scenario, epoch: int = 3, wet: float = 0.0) -> cap.Context:
    xy = sc.xy
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == xy)
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(*xy),
                       sc.matter["lithic_cells"], {"precipitation": wet * 3.0}, sc.consumers, epoch)


def _organic(sc: Scenario) -> float:
    return sum(mass(c[p]) for c in sc.producers["cells"] for p in ("plant_elements_kg", "woody_elements_kg", "detritus_elements_kg")) \
        + sum(mass(c["fresh_elements_kg"]) for c in sc.consumers["carcass_cells"]) + mass(cap.object_element_totals(sc.humans))


def test_extraction_needs_the_source_material_in_this_cell():
    sc = Scenario(capacities=True)
    sc.set_pool(1, 0, "plant_elements_kg", 10.0)
    sc.set_pool(1, 0, "woody_elements_kg", 10.0)
    sc.set_fresh_tissue(1, 0, 1.0)
    keys = [k for k, _ in cap.enumerate_affordances(_ctx(sc))]
    assert not any(k.startswith(("separate:plant_tissue", "separate:bark", "separate:tendon")) for k in keys), keys
    sc.set_pool(0, 0, "plant_elements_kg", 10.0)
    keys = [k for k, _ in cap.enumerate_affordances(_ctx(sc))]
    assert "separate:plant_tissue|none" in keys


def test_split_twist_weave_and_bind_conserve_material():
    sc = Scenario(capacities=True)
    sc.set_pool(0, 0, "plant_elements_kg", 20.0)
    sc.set_pool(0, 0, "woody_elements_kg", 20.0)
    total = _organic(sc)
    ctx = _ctx(sc)
    for i, (key, spec) in enumerate([
        ("separate:plant_tissue|none", {"verb": "extract_plant_fiber"}),
        ("separate:plant_tissue|none", {"verb": "extract_plant_fiber"}),
        ("twist:strands|held", {"verb": "twist"}),
        ("break:woody|none", {"verb": "wood_piece", "tool": None}),
        ("break:woody|none", {"verb": "wood_piece", "tool": None}),
        ("bind:x|strand", {"verb": "bind"}),
        ("interlace:strands|held", {"verb": "interlace"}),
    ]):
        cap.execute(_cp := _ctx(sc, i), key, spec)
        assert abs(_organic(sc) - total) < 1e-9, f"{key} changed organic mass"


def test_strength_and_wet_sensitivity_differ_by_source():
    tendon = mo.make_fiber("tendon", el(0.001), 0.5, 0.5, "t")
    plant = mo.make_fiber("plant", el(0.001), 0.5, 0.5, "p")
    bark = mo.make_fiber("bark", el(0.001), 0.5, 0.5, "b")
    assert mo.tensile_strength_n(tendon, 1.0) < 0.5 * mo.tensile_strength_n(tendon, 0.0)
    assert mo.tensile_strength_n(plant, 1.0) >= mo.tensile_strength_n(plant, 0.0)
    assert mo.tensile_strength_n(bark, 1.0) < mo.tensile_strength_n(bark, 0.0)
    twisted = mo.twist([mo.make_fiber("plant", el(0.001), 0.5, 0.5, f"p{i}") for i in range(3)], "c")
    assert mo.tensile_strength_n(twisted) > mo.tensile_strength_n(plant)


def test_binding_can_hold_slip_or_break():
    stone = {"id": "h", "material": "stone", "fragment": {"id": "h", "lith": "basaltic", "m": 0.4, "s": 0.1, "e": 1.2}}
    stick = mo.make_wood_piece(el(0.25), 0.6, 0.8, "k", 1.5)
    cord = mo.twist([mo.make_fiber("bark", el(0.002), 0.9, 0.5, f"b{i}") for i in range(3)], "cord")
    assert mo.wrap_and_tighten(cord, [stone, stick], 1e6, 0.0)["outcome"] == "broke"
    bound = mo.wrap_and_tighten(cord, [stone, stick], 60.0, 0.0)
    asm = {"components": [stone, stick], "binder": cord, "hold_n": bound["hold_n"]}
    assert mo.binding_load_result(asm, 1.0, 0.0) == "holds"
    assert mo.binding_load_result(dict(asm, hold_n=1.0), 5.0, 0.0) == "slips"
    assert mo.binding_load_result(asm, 1e7, 0.0) == "breaks"


def test_repeated_meaningless_fiber_actions_cost_and_are_not_reinforced():
    sc = Scenario(capacities=True)
    strand = mo.make_fiber("bark", el(0.002), 0.9, 0.5, "f0")
    sc.humans["objects"].append(cap._place(strand, 0, 0, sc.agent["id"]))
    values: dict = {}
    spent = 0.0
    for i in range(40):
        ctx = _ctx(sc, i)
        held = [o for o in sc.humans["objects"] if o["holder"] == sc.agent["id"] and o["material"] == "fiber"]
        if len(held) < cap.MAX_SOFT_IN_HAND:
            out = cap.execute(ctx, "separate:strand_bark|held", {"verb": "pull_apart", "id": held[0]["id"]})
        else:
            out = cap.execute(ctx, "release:strand_bark|none", {"verb": "release", "id": held[0]["id"]})
        ctx.performed.append(("separate:strand_bark|held", out))
        cap.learn_from_tick(ctx, [])
        spent += out["effort_kcal"]
        values = sc.agent["cognition"]["affordance_values"]
    assert spent >= 40 * cap.MIN_INTERACTION_KCAL
    assert all(float(v["v"]) < 0.0 for v in values.values()), values
