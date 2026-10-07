"""MICRO DIAGNOSTIC: what happens with fresh Agentus tissue?

This records the CURRENT behaviour. It does not decide the design. If a
future change makes conspecific tissue edible, these assertions fail on
purpose so the change is made as an explicit decision.
"""

from __future__ import annotations

from _scenario import Scenario, mass
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.diet import FOOD_KINDS, available_kg
from hrm_genesis.human.perception import extend_perception_with_materials, perceive_local


def _corpse_scenario():
    sc = Scenario(capacities=True, width=3)
    sc.set_water(0, 0, 50000.0)
    sc.add_agent("human-g00000009", 0, 0, energy=-1.0e7)  # dies of exhausted energy this tick
    sc.step(1)
    assert not any(h["id"] == "human-g00000009" for h in sc.humans["humans"])
    return sc


def test_agentus_remains_go_to_a_separate_pool_not_animal_carcass():
    sc = _corpse_scenario()
    # The body falls wherever the agent was when it died; look everywhere.
    assert sum(mass(c["elements_kg"]) for c in sc.humans["remains_cells"]) > 1.0
    for cell in sc.consumers["carcass_cells"]:
        assert mass(cell["fresh_elements_kg"]) == 0.0
        assert mass(cell["elements_kg"]) == 0.0


def test_conspecific_remains_are_not_a_food_kind_not_perceived_not_tasted():
    sc = _corpse_scenario()
    assert all(spec["pool"] != "remains" for spec in FOOD_KINDS.values())
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == (0, 0))
    assert available_kg("fresh_tissue", pcell, sc.carcass(0, 0)) == 0.0
    perception = perceive_local(sc.agent, sc.producers, sc.matter)
    extend_perception_with_materials(perception, sc.producers, sc.consumers, {}, [], {"plant_tissue": 1760.0}, 1760.0, {})
    here = next(c for c in perception["cells"] if (c["x"], c["y"]) == (0, 0))
    assert here["fresh_tissue_kg"] == 0.0 and here["decayed_tissue_kg"] == 0.0
    sc.agent["energy"] = 1000.0
    assert cap.choose_food_samples(sc.agent, pcell, sc.carcass(0, 0), 5, hungry=True) == ()


def test_agentus_are_not_capture_targets():
    sc = Scenario(capacities=True)
    sc.add_agent("human-g00000009", 0, 0)
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == (0, 0))
    ctx = cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(0, 0),
                      {}, {"precipitation": 0.0}, sc.consumers, 3)
    assert not any("human" in k for k, _ in cap.enumerate_affordances(ctx))


def test_report():
    """Printed by the micro runner; the assertions above are the evidence."""
    print(
        "\nCANNIBALISM DIAGNOSTIC (current behaviour, no design decision made):\n"
        "  classified as edible animal tissue: NO (Agentus remains go to human.remains_cells, never consumer carcasses)\n"
        "  already known as food: NO (no food kind reads remains)\n"
        "  learnable by tasting: NO (not offered for sampling)\n"
        "  transmissible by observation: NO (no ingestion event can occur)\n"
        "  explicit species/self/kin rule: NONE (the exclusion is architectural, not a rule)\n"
        "  possible in practice: NO. Agentus also cannot be capture targets, and animal\n"
        "  predators that injure Agentus never eat them. Any change here is a design decision."
    )
