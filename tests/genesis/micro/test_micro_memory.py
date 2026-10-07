"""MICRO: witnessed-event memory (G10.7a step 2). Perception -> memory only.

Agents remember who did what and what visibly followed. Nothing internal to
the actor is stored, and no decision reads the memory yet (imitation is a
later, separate step).
"""

from __future__ import annotations

import re
from pathlib import Path

from _scenario import Scenario
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.diet import innate_food_prior

ALLOWED_FIELDS = {"epoch", "actor", "act", "created", "eaten_kg", "hurt"}
KEY = "cut:fresh_tissue|stone_edged"
SEED_MEAL = {"kind": "seed", "kg": 1.0, "kcal": 2850.0, "hazard": 0.0, "handling_kcal": 60.0}


def _ctx(sc: Scenario, epoch: int = 7) -> cap.Context:
    xy = sc.xy
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == xy)
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(*xy),
                       sc.matter["lithic_cells"], {"precipitation": 0.0}, sc.consumers, epoch)


def _witness(sc: Scenario, aid: str = "witness", x: int = 0):
    w = sc.add_agent(aid, x, 0)
    w["cognition"]["food_values"] = innate_food_prior(sc.profile)
    return w


def _visible(kg=0.5, created=(), injury=0.0):
    return {"eaten_kg": {"fresh_tissue": kg} if kg else {}, "created": list(created), "injury": injury}


def test_a_witnessed_act_is_remembered_with_visible_fields_only():
    sc = Scenario(capacities=True)
    w = _witness(sc)
    cap.observe_outcome(_ctx(sc), KEY, reward=12.0, visible=_visible(0.5, created=["stone_edged"], injury=0.02))
    (event,) = w["cognition"]["witnessed"]
    assert set(event) == ALLOWED_FIELDS
    assert event == {"epoch": 7, "actor": sc.agent["id"], "act": KEY, "created": ["stone_edged"],
                     "eaten_kg": {"fresh_tissue": 0.5}, "hurt": True}


def test_it_is_remembered_even_when_it_means_nothing_to_the_witness():
    sc = Scenario(capacities=True)
    w = _witness(sc)  # has never eaten meat: no appraisal, but it still saw it
    cap.observe_outcome(_ctx(sc), KEY, visible=_visible(0.5))
    assert KEY not in w["cognition"]["affordance_values"]
    assert w["cognition"]["witnessed"][0]["act"] == KEY


def test_witnessed_eating_records_the_material_and_visible_distress():
    sc = Scenario(capacities=True)
    w = _witness(sc)
    cap.observe_food(_ctx(sc), [SEED_MEAL, {"kind": "decayed_tissue", "kg": 0.1, "kcal": 0.0, "hazard": 0.06, "handling_kcal": 2.0}])
    acts = [(e["act"], e["hurt"]) for e in w["cognition"]["witnessed"]]
    assert acts == [("eat:seed", False), ("eat:decayed_tissue", True)]


def test_only_agents_in_the_same_cell_remember_and_the_actor_does_not_witness_itself():
    sc = Scenario(capacities=True)
    far = _witness(sc, "far", x=3)
    cap.observe_outcome(_ctx(sc), KEY, visible=_visible())
    cap.observe_food(_ctx(sc), [SEED_MEAL])
    assert "witnessed" not in far["cognition"]
    assert "witnessed" not in sc.agent["cognition"]


def test_dependents_witness_too():
    sc = Scenario(capacities=True)
    child = _witness(sc, "human-b00000001")
    child["age_ticks"] = 200
    cap.observe_food(_ctx(sc), [SEED_MEAL])
    assert child["cognition"]["witnessed"][0]["act"] == "eat:seed"


def test_memory_is_bounded_and_keeps_the_newest():
    sc = Scenario(capacities=True)
    w = _witness(sc)
    for epoch in range(cap.WITNESSED_MEMORY + 10):
        cap.observe_food(_ctx(sc, epoch), [SEED_MEAL])
    events = w["cognition"]["witnessed"]
    assert len(events) == cap.WITNESSED_MEMORY
    assert events[0]["epoch"] == 10 and events[-1]["epoch"] == cap.WITNESSED_MEMORY + 9


def test_memory_off_and_legacy_observation_store_nothing():
    for kwargs in ({"memory": False}, {"observation": "g10.4-legacy"}):
        sc = Scenario(capacities=True, **kwargs)
        w = _witness(sc)
        cap.observe_outcome(_ctx(sc), KEY, reward=0.4, visible=_visible())
        cap.observe_food(_ctx(sc), [SEED_MEAL])
        assert "witnessed" not in w["cognition"], kwargs


def test_no_decision_code_reads_witnessed_memory():
    """Step 2 is perception -> memory only. The only code that may touch the
    memory is the function that writes it."""
    src = Path(__file__).resolve().parents[3] / "src" / "hrm_genesis"
    touches: set[str] = set()
    for path in src.rglob("*.py"):
        text = path.read_text()
        for m in re.finditer(r"\"witnessed\"", text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line = text[line_start:text.find("\n", m.start())].strip()
            touches.add(f"{path.name}: {line}")
    allowed = 'cognition["witnessed"] = (list(cognition.get("witnessed", [])) + [entry])[-WITNESSED_MEMORY:]'
    assert touches == {f"interactions.py: {allowed}"}, touches
