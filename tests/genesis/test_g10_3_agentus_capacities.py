"""G10.3 capacity model v1: qualification of physical capability.

These tests show that mechanisms work and conserve material. They are not
evidence that Agentus discover anything; several fixtures place objects in
hand directly, which is seeded setup, not behavior.
"""

from __future__ import annotations

from copy import deepcopy

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import consumer_element_totals, enable_fresh_tissue, kill_animal
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.biology import evolve_agentus_step
from hrm_genesis.human.diet import forage_at_cell, ingest, innate_food_prior
from hrm_genesis.human.calibration import reference_adult_profile
from hrm_genesis.human.perception import extend_perception_with_materials, perceive_local
from hrm_genesis.human.planning import choose_destination
from hrm_genesis.matter import objects as mo


FRACTIONS = {"C": 0.86, "N": 0.08, "K": 0.025, "P": 0.012, "Mg": 0.013, "S": 0.01}


def _el(kg: float) -> dict[str, float]:
    return {s: kg * f for s, f in FRACTIONS.items()}


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def _profile() -> dict:
    profile = dict(reference_adult_profile(365))
    profile["development_scale"] = 1.0
    profile["target_dry_mass_kg"] = profile["seed_dry_mass_kg"]
    return profile


def _pcell(plant=0.0, seed=0.0, woody=0.0) -> dict:
    return {
        "x": 0, "y": 0,
        "plant_elements_kg": _el(plant),
        "seed_elements_kg": _el(seed),
        "woody_elements_kg": _el(woody),
        "loose_material_elements_kg": _el(0.0),
        "arranged_material_elements_kg": _el(0.0),
        "detritus_elements_kg": _el(0.0),
        "fire_intensity": 0.0,
    }


def _ccell(fresh=0.0, decayed=0.0) -> dict:
    return {"x": 0, "y": 0, "elements_kg": _el(decayed), "fresh_elements_kg": _el(fresh), "water_kg": 0.0}


def _agent(energy=10000.0, dry_kg=20.0) -> dict:
    return {
        "id": "agent-a", "x": 0, "y": 0, "energy": energy,
        "body_elements_kg": _el(dry_kg), "body_water_kg": 42.0,
        "fatigue": 0.0, "injury": 0.0, "age_ticks": 10000,
        "held_material_elements_kg": _el(0.0),
        "cognition": {"memory": {"episodes": [], "locations": {}}, "food_values": {}, "affordance_values": {}, "trace": []},
    }


def _humans(*agents) -> dict:
    return {"humans": list(agents), "objects": [], "next_object_ordinal": 0, "capacity_stats": cap.empty_stats()}


def _ctx(humans, agent, pcell, ccell=None, lithic=None, animals=None, wet=0.0):
    consumers = {"width": 3, "height": 3, "animals": animals or [], "carcass_cells": [], "cumulative_deaths_by_cause": {}}
    return cap.Context(humans, agent, _profile(), pcell, ccell or _ccell(), lithic or {}, {"precipitation": wet * 3.0}, consumers, 7)


def _stone_obj(lith, mass, sharp, holder="agent-a", oid="s1", elong=1.5) -> dict:
    frag = {"id": oid, "lith": lith, "m": mass, "s": sharp, "e": elong}
    return {"id": oid, "material": "stone", "fragment": frag, "x": 0, "y": 0, "holder": holder, "worn": False}


# --- Consumption and conservation ------------------------------------------


def test_ingestion_moves_real_mass_without_duplication():
    agent, pcell = _agent(energy=2000.0), _pcell(seed=2.0)
    before = _mass(pcell["seed_elements_kg"]) + _mass(agent["body_elements_kg"]) + _mass(pcell["detritus_elements_kg"])
    rec = ingest(agent, "seed", 1.0, pcell, None, _profile())
    after = _mass(pcell["seed_elements_kg"]) + _mass(agent["body_elements_kg"]) + _mass(pcell["detritus_elements_kg"])
    assert rec["kg"] > 0.0
    assert abs(before - after) < 1e-12
    assert rec["kg"] <= 0.45 + 1e-12  # hand gathering limit for dispersed seed


def test_energy_from_plant_seed_and_animal_sources():
    profile = _profile()
    for kind, pcell, ccell in [
        ("plant_tissue", _pcell(plant=1.0), None),
        ("seed", _pcell(seed=1.0), None),
        ("fresh_tissue", _pcell(), _ccell(fresh=1.0)),
    ]:
        agent = _agent(energy=1000.0)
        rec = ingest(agent, kind, 0.2, pcell, ccell, profile)
        assert rec["kcal"] > 0.0, kind
        assert agent["energy"] > 1000.0, kind


def test_unsupported_material_is_not_food():
    profile = _profile()
    wood_eater = _agent(energy=1000.0)
    rec = ingest(wood_eater, "woody_tissue", 0.1, _pcell(woody=5.0), None, profile)
    assert rec["kg"] > 0.0 and rec["kcal"] == 0.0
    assert wood_eater["energy"] < 1000.0  # handling cost, no gain

    carrion_eater = _agent(energy=1000.0)
    rec = ingest(carrion_eater, "decayed_tissue", 0.2, _pcell(), _ccell(decayed=1.0), profile)
    assert rec["kcal"] == 0.0 and rec["hazard"] > 0.0
    assert carrion_eater["injury"] > 0.0

    # Unknown kinds are not eaten except as an explicit, bounded sample.
    agent, pcell = _agent(energy=1000.0), _pcell(seed=5.0, woody=5.0)
    records = forage_at_cell(agent, pcell, None, profile, innate_food_prior(profile))
    assert records == []
    assert abs(_mass(pcell["seed_elements_kg"]) - 5.0) < 1e-12


def test_animal_killed_once_and_body_enters_fresh_carcass_pool():
    sim = GenesisSimulation(GenesisConfig(master_seed="g10-3-kill", producer_ecology_enabled=True, consumer_ecology_enabled=True))
    consumers = enable_fresh_tissue(sim.consumer_state())
    assert consumers["animals"]
    total_before = consumer_element_totals(consumers)
    victim = consumers["animals"][0]
    count_before = len(consumers["animals"])
    killed = kill_animal(consumers, victim["id"], "agentus")
    assert killed is not None
    assert len(consumers["animals"]) == count_before - 1
    assert kill_animal(consumers, victim["id"], "agentus") is None
    assert consumers["cumulative_deaths_by_cause"]["agentus"] == 1
    total_after = consumer_element_totals(consumers)
    assert all(abs(total_before[s] - total_after[s]) < 1e-9 for s in total_before)
    cell = next(c for c in consumers["carcass_cells"] if (c["x"], c["y"]) == (victim["x"], victim["y"]))
    assert _mass(cell["fresh_elements_kg"]) >= _mass(victim["body_elements_kg"]) - 1e-12


def test_capture_attempt_can_fail_and_prey_escapes():
    humans = _humans(_agent())
    agent = humans["humans"][0]
    animal = {"id": "browser-x", "species": "browser", "x": 1, "y": 1, "energy": 40.0,
              "body_elements_kg": _el(0.06), "body_water_kg": 0.2}
    outcomes = set()
    for epoch in range(40):
        consumers = {"width": 3, "height": 3, "animals": [deepcopy(animal)],
                     "carcass_cells": [_ccell() | {"x": x, "y": y} for y in range(3) for x in range(3)],
                     "cumulative_deaths_by_cause": {}}
        a = deepcopy(agent); a["x"], a["y"] = 1, 1
        ctx = cap.Context(_humans(a), a, _profile(), _pcell(), consumers["carcass_cells"][4], {}, {}, consumers, epoch)
        out = cap.execute(ctx, "strike:animal_browser|none", {"verb": "capture", "tool": None, "animal": "browser-x"})
        outcomes.add(bool(out.get("capture")))
        if out.get("capture"):
            assert consumers["animals"] == []
        else:
            assert (consumers["animals"][0]["x"], consumers["animals"][0]["y"]) != (1, 1)
        assert a["energy"] < agent["energy"]
    assert outcomes == {True, False}


# --- Stone ------------------------------------------------------------------


def test_fracture_conserves_mass_and_sharpness_is_not_automatic():
    sharp, blunt = 0, 0
    for i in range(60):
        lith = ("siliceous_fine", "granitic_coarse")[i % 2]
        frag = {"id": f"t{i}", "lith": lith, "m": 1.0, "s": 0.1, "e": 1.2}
        energy = mo.stone_props(frag)["fracture_energy_j"] * 1.5
        core, flake = mo.fracture(frag, energy, mo.unit_draw(i, "a"), mo.unit_draw(i, "b"), f"f{i}")
        assert abs(core["m"] + flake["m"] - 1.0) < 1e-9
        if flake["s"] >= 0.4:
            sharp += 1
            assert lith == "siliceous_fine"
        else:
            blunt += 1
    assert sharp > 0 and blunt > 0
    weak = {"id": "w", "lith": "granitic_coarse", "m": 2.0, "s": 0.1, "e": 1.0}
    assert mo.fracture(weak, mo.stone_props(weak)["fracture_energy_j"] * 0.9, 0.5, 0.5, "x") is None


def test_strike_outcome_depends_on_hammer_properties():
    def strike(hammer, target_lith):
        humans = _humans(_agent())
        agent = humans["humans"][0]
        humans["objects"].append(hammer)
        lithic = {"0,0": [{"id": "target", "lith": target_lith, "m": 0.6, "s": 0.1, "e": 1.0}]}
        before = sum(f["m"] for f in lithic["0,0"]) + mo.object_lithic_mass(hammer)
        ctx = _ctx(humans, agent, _pcell(), lithic=lithic)
        cap.execute(ctx, "strike:stone_heavy|x", {"verb": "strike_stone", "tool": hammer["id"], "natural": "target"})
        after = cap.lithic_inventory_kg({"lithic_cells": lithic}, humans)
        assert abs(before - after) < 1e-9
        return ctx.stats["fractures"] > 0

    heavy_hard = _stone_obj("basaltic", 1.0, 0.1, oid="hammer")
    light_soft = _stone_obj("calcareous_soft", 0.05, 0.1, oid="pebble")
    assert strike(heavy_hard, "siliceous_fine")
    assert not strike(light_soft, "granitic_coarse")


def test_edge_cuts_and_dulls_while_blunt_stone_does_not_cut():
    sharp = {"id": "a", "lith": "siliceous_fine", "m": 0.1, "s": 0.8, "e": 3.0}
    blunt = {"id": "b", "lith": "granitic_coarse", "m": 0.8, "s": 0.05, "e": 1.0}
    c_sharp = mo.cutting_capacity(sharp["s"], 7.0, 0.5, 1.0)
    c_blunt = mo.cutting_capacity(blunt["s"], 6.0, 0.5, 1.0)
    assert c_sharp > 10 * c_blunt
    before = sharp["s"]
    mo.edge_wear(sharp, 2.0)
    assert sharp["s"] < before


# --- Fibers and binding -----------------------------------------------------


def test_fiber_extraction_and_manipulation_conserve_material():
    humans = _humans(_agent())
    agent = humans["humans"][0]
    pcell = _pcell(plant=3.0)
    start = _mass(pcell["plant_elements_kg"])
    ctx = _ctx(humans, agent, pcell)
    cap.execute(ctx, "separate:plant_tissue|none", {"verb": "extract_plant_fiber"})
    fibers = [o for o in humans["objects"] if o["material"] == "fiber"]
    assert fibers
    total = lambda: _mass(pcell["plant_elements_kg"]) + _mass(cap.object_element_totals(humans))
    assert abs(total() - start) < 1e-12
    cap.execute(ctx, "twist:strands|held", {"verb": "twist"})
    cap.execute(ctx, "separate:x|held", {"verb": "pull_apart", "id": humans["objects"][0]["id"]})
    assert abs(total() - start) < 1e-12
    # Repeating a manipulation never creates fiber.
    for _ in range(5):
        cap.execute(ctx, "twist:strands|held", {"verb": "twist"})
    assert abs(total() - start) < 1e-12


def test_source_properties_differ_and_moisture_matters():
    tendon = mo.make_fiber("tendon", _el(0.001), 0.5, 0.5, "t")
    plant = mo.make_fiber("plant", _el(0.001), 0.5, 0.5, "p")
    assert mo.tensile_strength_n(tendon, 1.0) < 0.5 * mo.tensile_strength_n(tendon, 0.0)
    assert mo.tensile_strength_n(plant, 1.0) >= mo.tensile_strength_n(plant, 0.0)
    assert tendon["length_m"] < plant["length_m"]


def _hafted(binder_strands: int) -> tuple[dict, dict]:
    stone = {"id": "head", "material": "stone", "fragment": {"id": "head", "lith": "basaltic", "m": 0.4, "s": 0.1, "e": 1.2}}
    stick = mo.make_wood_piece(_el(0.25), 0.6, 0.8, "stick", 1.5)
    strands = [mo.make_fiber("bark", _el(0.002), 0.9, 0.5, f"b{i}") for i in range(binder_strands)]
    binder = strands[0] if binder_strands == 1 else mo.twist(strands, "cord")
    return stone, stick, binder


def test_binding_constrains_holds_and_can_fail():
    stone, stick, binder = _hafted(3)
    # Overtightening breaks the strand.
    over = mo.wrap_and_tighten(binder, [stone, stick], 1e6, 0.0)
    assert over["outcome"] == "broke"
    result = mo.wrap_and_tighten(binder, [stone, stick], 60.0, 0.0)
    assert result["outcome"] == "bound"
    assembly = {"id": "asm", "material": "assembly", "components": [stone, stick], "binder": binder, "hold_n": result["hold_n"]}
    assert mo.binding_load_result(assembly, 1.0, 0.0) == "holds"
    assert mo.binding_load_result(assembly, 1e7, 0.0) == "breaks"
    small_hold = dict(assembly, hold_n=1.0)
    assert mo.binding_load_result(small_hold, 5.0, 0.0) == "slips"
    # A strand too short for one turn cannot bind anything.
    short = mo.make_fiber("tendon", _el(0.0001), 0.0, 0.5, "short")
    assert mo.wrap_and_tighten(short, [stone, stick], 10.0, 0.0)["outcome"] == "short"


def test_bound_handle_changes_impact_and_occupies_one_hand():
    stone, stick, binder = _hafted(3)
    head_mass = stone["fragment"]["m"]
    loose = mo.impact_energy_j(head_mass, 120.0, 9.0, 0.0)
    levered = mo.impact_energy_j(head_mass, 120.0, 9.0, stick["length_m"])
    assert levered > loose
    result = mo.wrap_and_tighten(binder, [stone, stick], 60.0, 0.0)
    assembly = {"id": "asm", "material": "assembly", "components": [stone, stick], "binder": binder, "hold_n": result["hold_n"], "x": 0, "y": 0, "holder": "agent-a", "worn": False}
    humans = _humans(_agent())
    humans["objects"].append(assembly)
    ctx = _ctx(humans, humans["humans"][0], _pcell())
    assert len(ctx.rigid_held()) == 1  # two objects constrained together
    assert cap._head_and_lever(assembly)[1] == stick["length_m"]


def test_bind_action_in_live_interaction_conserves_and_reports_outcome():
    humans = _humans(_agent())
    agent = humans["humans"][0]
    stone, stick, binder = _hafted(3)
    for obj in (stone, stick, binder):
        humans["objects"].append(cap._place(obj, 0, 0, "agent-a"))
    elements_before = _mass(cap.object_element_totals(humans))
    lithic_before = cap.lithic_inventory_kg({}, humans)
    ctx = _ctx(humans, agent, _pcell())
    out = cap.execute(ctx, "bind:x|strand", {"verb": "bind"})
    assert out["bind_outcome"] in {"bound", "broke", "short", "too_stiff"}
    assert abs(_mass(cap.object_element_totals(humans)) - elements_before) < 1e-12
    assert abs(cap.lithic_inventory_kg({}, humans) - lithic_before) < 1e-12


# --- Perception, learning, choice -------------------------------------------


def test_material_perception_stays_local():
    sim = GenesisSimulation(GenesisConfig(master_seed="g10-3-percept", producer_ecology_enabled=True, consumer_ecology_enabled=True))
    producers, consumers = sim.ecology_state(), enable_fresh_tissue(sim.consumer_state())
    agent = _agent()
    agent["x"], agent["y"] = 4, 4
    perception = perceive_local(agent, producers, sim.matter_state())
    extend_perception_with_materials(perception, producers, consumers, {}, [], {"plant_tissue": 1760.0}, 1760.0, {})
    for cell in perception["cells"]:
        assert abs(cell["x"] - 4) + abs(cell["y"] - 4) <= 1
        assert "expected_food_kg" in cell
    assert len(perception["cells"]) <= 5


def test_experience_changes_later_food_choice():
    profile = _profile()
    naive = _agent(energy=1000.0)
    naive["cognition"]["food_values"] = innate_food_prior(profile)
    pcell = _pcell(seed=5.0)
    assert forage_at_cell(naive, deepcopy(pcell), None, profile, naive["cognition"]["food_values"]) == []
    # One sample, learned from the body's own result.
    samples = forage_at_cell(naive, pcell, None, profile, naive["cognition"]["food_values"], ("seed",))
    ctx = _ctx(_humans(naive), naive, pcell)
    cap.learn_from_tick(ctx, samples)
    assert naive["cognition"]["food_values"]["seed"] > 0.0
    later = forage_at_cell(naive, pcell, None, profile, naive["cognition"]["food_values"])
    assert any(r["kind"] == "seed" and r["kg"] > 0.0 for r in later)

    # The same sampling of wood teaches the opposite.
    wary = _agent(energy=1000.0)
    wary["cognition"]["food_values"] = innate_food_prior(profile)
    wood = _pcell(woody=5.0)
    samples = forage_at_cell(wary, wood, None, profile, wary["cognition"]["food_values"], ("woody_tissue",))
    cap.learn_from_tick(_ctx(_humans(wary), wary, wood), samples)
    assert wary["cognition"]["food_values"]["woody_tissue"] < 0.0
    assert forage_at_cell(wary, wood, None, profile, wary["cognition"]["food_values"]) == []


def test_learned_interaction_value_changes_choice_and_planning_uses_expectations():
    humans = _humans(_agent())
    agent = humans["humans"][0]
    ctx = _ctx(humans, agent, _pcell(plant=3.0))
    options = cap.enumerate_affordances(ctx)
    keys = [k for k, _ in options]
    assert "separate:plant_tissue|none" in keys
    assert cap.choose(ctx, options, 0, hungry=False) is None or agent["cognition"]["affordance_values"] == {}
    agent["cognition"]["affordance_values"] = {"separate:plant_tissue|none": {"n": 3, "v": 0.5}}
    assert cap.choose(ctx, options, 0, hungry=False)[0] == "separate:plant_tissue|none"

    perception = {"origin": [1, 1], "forage_need_kg": 1.0, "energy_reserve_fraction": 0.2, "cells": [
        {"x": 1, "y": 1, "food_kg": 0.0, "expected_food_kg": 0.0, "water_kg": 1.0},
        {"x": 2, "y": 1, "food_kg": 0.0, "expected_food_kg": 2.0, "water_kg": 1.0},
        {"x": 0, "y": 1, "food_kg": 0.5, "expected_food_kg": 0.5, "water_kg": 1.0},
    ]}
    assert choose_destination({}, perception, {}) == (2, 1)


def test_hungry_agent_returns_toward_remembered_food():
    perception = {"origin": [3, 3], "forage_need_kg": 1.0, "energy_reserve_fraction": 0.2,
                  "remembered_food": [[6, 3, 5.0, 10], [3, 0, 0.1, 12]],
                  "cells": [{"x": 3, "y": 3, "food_kg": 0.0, "water_kg": 1.0},
                            {"x": 4, "y": 3, "food_kg": 0.0, "water_kg": 1.0},
                            {"x": 2, "y": 3, "food_kg": 0.0, "water_kg": 1.0},
                            {"x": 3, "y": 2, "food_kg": 0.0, "water_kg": 1.0}]}
    assert choose_destination({}, perception, {}) == (4, 3)


# --- Integration: infants, replay, compatibility ----------------------------


def _capacity_config(seed: str) -> GenesisConfig:
    return GenesisConfig(
        master_seed=seed, world_width=8, world_height=8, ticks_per_year=365,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, human_biology_enabled=True,
        human_cognition_enabled=True, human_actions_enabled=True, multi_population_enabled=True,
        material_scale_factor=1000.0, human_calibration_enabled=True, agentus_capacities_enabled=True,
    )


def test_infants_do_not_forage_or_interact():
    sim = GenesisSimulation(_capacity_config("g10-3-infant"))
    humans = sim.human_state()
    mother = humans["humans"][0]
    infant = deepcopy(mother)
    infant.update(id="human-b99999999", age_ticks=10, energy=500.0, caregiver_id="nobody")
    infant["cognition"]["affordance_values"] = {}
    humans["humans"] = [infant]
    pcells = sim.ecology_state()
    for cell in pcells["cells"]:
        if (cell["x"], cell["y"]) == (infant["x"], infant["y"]):
            cell["plant_elements_kg"] = _el(10.0)
    next_humans, *_ = evolve_agentus_step(
        humans, pcells, sim.matter_state(), sim.world_state(), 1,
        cognition_enabled=True, actions_enabled=True, consumer_state=sim.consumer_state(),
    )
    stats = next_humans["capacity_stats"]
    assert stats["interaction_counts"] == {}
    assert stats["intake_kg_by_kind"] == {}


def test_capacity_run_is_deterministic_conserving_and_replayable(tmp_path):
    from qualification.genesis.run_g5_human_biology_gate import combined_element_errors, combined_water_error

    a = GenesisSimulation(_capacity_config("g10-3-replay"))
    b = GenesisSimulation(_capacity_config("g10-3-replay"))
    a.run(25)
    b.run(25)
    assert a.ledger.digest() == b.ledger.digest()
    assert a.ledger.verify_chain()
    assert max(abs(v) for v in combined_element_errors(a).values()) < 1e-6
    assert abs(combined_water_error(a)) < 1e-6
    lithic = cap.lithic_inventory_kg(a.matter_state(), a.human_state())
    assert abs(lithic - a.matter_state()["initial_lithic_kg"]) < 1e-6

    path = tmp_path / "cap.json"
    a.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, _capacity_config("g10-3-replay"))
    a.run(5)
    restored.run(5)
    assert restored.ledger.digest() == a.ledger.digest()


def test_flag_off_keeps_earlier_fingerprints():
    base = dict(_capacity_config("x").canonical())
    off = GenesisConfig(
        master_seed="x", world_width=8, world_height=8, ticks_per_year=365,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, human_biology_enabled=True,
        human_cognition_enabled=True, human_actions_enabled=True, multi_population_enabled=True,
        material_scale_factor=1000.0, human_calibration_enabled=True,
    ).canonical()
    assert "agentus_capacities_enabled" not in off
    assert base["agentus_capacity_model"] == "capacity-v1"
    sim = GenesisSimulation(GenesisConfig(master_seed="x", producer_ecology_enabled=True, consumer_ecology_enabled=True))
    assert all("fresh_elements_kg" not in c for c in sim.consumer_state()["carcass_cells"])


def test_plant_only_expectation_leaves_pre_capacity_planning_unchanged():
    """Regression: a per-day gathering cap on plant tissue once saturated
    perceived food in rich cells and silently changed planning (water became
    the tie-breaker). With only plant tissue valued, the planner must see the
    same food numbers as before G10.3."""
    sim = GenesisSimulation(GenesisConfig(master_seed="g10-3-plan", producer_ecology_enabled=True, consumer_ecology_enabled=True))
    producers = sim.ecology_state()
    for cell in producers["cells"]:
        cell["plant_elements_kg"] = _el(500.0 + cell["x"])
    consumers = enable_fresh_tissue(sim.consumer_state())
    profile = _profile()
    agent = _agent()
    agent["x"], agent["y"] = 3, 3
    perception = perceive_local(agent, producers, sim.matter_state())
    from hrm_genesis.human.diet import FOOD_KINDS
    access = {k: float(v["hand_access_kg"]) for k, v in FOOD_KINDS.items() if v["hand_access_kg"] is not None}
    extend_perception_with_materials(perception, producers, consumers, {}, [], innate_food_prior(profile), innate_food_prior(profile)["plant_tissue"], access)
    for cell in perception["cells"]:
        assert abs(cell["expected_food_kg"] - cell["food_kg"]) < 1e-6
