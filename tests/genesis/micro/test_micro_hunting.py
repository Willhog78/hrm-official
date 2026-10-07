"""MICRO: hunting. Capture must be physically earned and pay real costs."""

from __future__ import annotations

from copy import deepcopy

from _scenario import Scenario, el, mass
from hrm_genesis.ecology.animals import evolve_consumers, kill_animal, spoilage_fraction
from hrm_genesis.human import interactions as cap


def _ctx(sc: Scenario, epoch: int = 7) -> cap.Context:
    xy = sc.xy
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == xy)
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(*xy),
                       sc.matter["lithic_cells"], {"precipitation": 0.0}, sc.consumers, epoch)


def test_animal_in_another_cell_is_not_offered_and_cannot_be_grabbed():
    sc = Scenario(capacities=True)
    sc.set_agent(0, 0)
    sc.add_animal("grazer-far", "grazer", 1, 0)
    ctx = _ctx(sc)
    assert not any(k.startswith("strike:animal") for k, _ in cap.enumerate_affordances(ctx))
    # Even a forged request cannot act at a distance.
    out = cap.execute(ctx, "strike:animal_grazer|none", {"verb": "capture", "tool": None, "animal": "grazer-far"})
    assert not out.get("capture") and len(sc.consumers["animals"]) == 1
    assert ctx.stats.get("capture_attempts", 0) == 0


def test_capture_requires_approach_and_both_outcomes_occur_with_real_costs():
    outcomes, costs = {}, []
    for epoch in range(60):
        sc = Scenario(capacities=True)
        sc.set_agent(0, 0)
        sc.add_animal("grazer-1", "grazer", 0, 0, energy=40.0)
        ctx = _ctx(sc, epoch)
        e0 = sc.agent["energy"]
        out = cap.execute(ctx, "strike:animal_grazer|none", {"verb": "capture", "tool": None, "animal": "grazer-1"})
        enc = out["encounter"]
        outcomes[enc["outcome"]] = outcomes.get(enc["outcome"], 0) + 1
        spent = e0 - sc.agent["energy"]
        expected = 5.0 + cap.ENCOUNTER_WALK_KCAL_PER_M * enc["walked_m"] + cap.ENCOUNTER_SPRINT_KCAL_PER_M * enc["sprinted_m"]
        assert abs(spent - expected) < 1e-6, f"cost {spent} does not match distance covered {expected}"
        if enc["outcome"] == "kill":
            assert enc["contact"]
        else:
            moved = [a for a in sc.consumers["animals"] if a["id"] == "grazer-1"]
            assert moved and (moved[0]["x"], moved[0]["y"]) != (0, 0), "escaped prey must flee the cell"
        costs.append(spent)
    assert "kill" in outcomes and ({"outrun", "reached_cover"} & set(outcomes)), outcomes
    assert min(costs) > 0.0, "every hunt, failed or not, must cost energy"


def test_a_kill_yields_real_tissue_exactly_once():
    sc = Scenario(capacities=True)
    animal = sc.add_animal("browser-1", "browser", 0, 0, body_kg=0.06)
    body = mass(animal["body_elements_kg"])
    count = len(sc.consumers["animals"])
    killed = kill_animal(sc.consumers, "browser-1", "agentus")
    assert killed is not None and len(sc.consumers["animals"]) == count - 1
    assert abs(mass(sc.carcass(0, 0)["fresh_elements_kg"]) - body) < 1e-12
    assert kill_animal(sc.consumers, "browser-1", "agentus") is None
    assert abs(mass(sc.carcass(0, 0)["fresh_elements_kg"]) - body) < 1e-12, "tissue duplicated by a second kill"


def test_fresh_tissue_spoils_faster_warm_than_cold_and_conserves_mass():
    warm, cold = Scenario(capacities=True), Scenario(capacities=True)
    for sc, temp in ((warm, 30.0), (cold, 0.0)):
        sc.set_fresh_tissue(0, 0, 1.0)
        for cell in sc.world["cells"]:
            cell["temperature"] = temp
    results = {}
    for name, sc in (("warm", warm), ("cold", cold)):
        consumers, producers, matter = deepcopy(sc.consumers), deepcopy(sc.producers), deepcopy(sc.matter)
        soil0 = sum(mass(c["elements_kg"]) for c in matter["cells"])
        total0 = sum(mass(c["fresh_elements_kg"]) + mass(c["elements_kg"]) for c in consumers["carcass_cells"]) + soil0
        consumers, producers, matter = evolve_consumers(consumers, producers, matter, sc.world, 1)
        fresh = mass(next(c for c in consumers["carcass_cells"] if (c["x"], c["y"]) == (0, 0))["fresh_elements_kg"])
        total1 = (sum(mass(c["fresh_elements_kg"]) + mass(c["elements_kg"]) for c in consumers["carcass_cells"])
                  + sum(mass(c["elements_kg"]) for c in matter["cells"]))
        assert abs(total1 - total0) < 1e-6
        results[name] = fresh
    assert results["warm"] < results["cold"] < 1.0
    assert spoilage_fraction(30.0, 365) > spoilage_fraction(0.0, 365)


def test_capture_with_a_held_stick_extends_reach_but_a_stick_lying_nearby_does_not():
    sc = Scenario(capacities=True)
    sc.set_agent(0, 0)
    sc.add_animal("grazer-1", "grazer", 0, 0)
    stick = {"id": "stick", "material": "wood", "elements_kg": el(0.3), "length_m": 1.4, "diameter_m": 0.03,
             "stiffness": 0.8, "x": 0, "y": 0, "holder": None, "worn": False}
    sc.humans["objects"].append(stick)
    ctx = _ctx(sc)
    keys = [k for k, _ in cap.enumerate_affordances(ctx)]
    assert "strike:animal_grazer|none" in keys and "strike:animal_grazer|stick" not in keys
    stick["holder"] = sc.agent["id"]
    keys = [k for k, _ in cap.enumerate_affordances(ctx)]
    assert "strike:animal_grazer|stick" in keys
