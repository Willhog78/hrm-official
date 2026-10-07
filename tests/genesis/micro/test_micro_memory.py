"""MICRO: witnessed-event memory (G10.7a step 2). Perception -> memory only.

Agents remember who did what and what visibly followed. Nothing internal to
the actor is stored, and no decision reads the memory yet (imitation is a
later, separate step).
"""

from __future__ import annotations

import ast
from pathlib import Path

from _scenario import Scenario
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.diet import innate_food_prior

STEP2_FIELDS = {"epoch", "actor", "act", "created", "eaten_kg", "hurt"}
CONSEQUENCE_FIELDS = {"appeared", "transformed", "killed", "exposed_kg"}
ALLOWED_FIELDS = STEP2_FIELDS | CONSEQUENCE_FIELDS
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
    assert {k: event[k] for k in STEP2_FIELDS} == {"epoch": 7, "actor": sc.agent["id"], "act": KEY, "created": ["stone_edged"],
                                                   "eaten_kg": {"fresh_tissue": 0.5}, "hurt": True}


def test_fifo_retention_stores_exactly_the_step_2_fields():
    sc = Scenario(capacities=True, retention="fifo")
    w = _witness(sc)
    cap.observe_outcome(_ctx(sc), KEY, visible=_visible(0.5))
    assert set(w["cognition"]["witnessed"][0]) == STEP2_FIELDS


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
    sc = Scenario(capacities=True, retention="fifo")
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


def test_only_the_writer_and_the_imitation_reader_touch_witnessed_memory():
    """Every reference to the memory in the model sits inside the function that
    writes it or the one declared reader, imitation (step 3)."""
    src = Path(__file__).resolve().parents[3] / "src" / "hrm_genesis"
    outside = []

    def visit(node, enclosing):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            enclosing = node.name
        if isinstance(node, ast.Constant) and node.value == "witnessed" and enclosing not in {"remember_witnessed", "imitation_candidate"}:
            outside.append(f"{path.name}:{node.lineno} in {enclosing}")
        for child in ast.iter_child_nodes(node):
            visit(child, enclosing)

    for path in src.rglob("*.py"):
        visit(ast.parse(path.read_text()), "<module>")
    assert outside == [], outside


# --- Step 2.5: conspicuous things stick better --------------------------------


def _fill_with_meals(sc, w, n, start=0):
    for epoch in range(start, start + n):
        cap.observe_food(_ctx(sc, epoch), [SEED_MEAL])


def test_a_conspicuous_act_outlasts_routine_meals():
    sc = Scenario(capacities=True)
    w = _witness(sc)
    flake = dict(_visible(0.0, created=["stone_edged"]), appeared=["stone_edged"], transformed=True)
    cap.observe_outcome(_ctx(sc, 0), "strike:stone_small|stone_heavy", visible=flake)
    _fill_with_meals(sc, w, cap.WITNESSED_MEMORY + 20, start=1)
    acts = [e["act"] for e in w["cognition"]["witnessed"]]
    assert "strike:stone_small|stone_heavy" in acts and len(acts) == cap.WITNESSED_MEMORY


def test_under_fifo_the_same_act_is_flushed():
    sc = Scenario(capacities=True, retention="fifo")
    w = _witness(sc)
    cap.observe_outcome(_ctx(sc, 0), "strike:stone_small|stone_heavy", visible=_visible(0.0, created=["stone_edged"]))
    _fill_with_meals(sc, w, cap.WITNESSED_MEMORY + 20, start=1)
    assert "strike:stone_small|stone_heavy" not in [e["act"] for e in w["cognition"]["witnessed"]]


def test_salience_comes_from_visible_consequences_not_from_the_act_name():
    base = {"epoch": 0, "actor": "a", "created": [], "eaten_kg": {}, "hurt": False,
            "appeared": [], "transformed": False, "killed": False, "exposed_kg": 0.0}
    assert cap.witnessed_salience(dict(base, act="strike:stone_small|stone_heavy")) == 0  # nothing happened
    assert cap.witnessed_salience(dict(base, act="eat:seed", eaten_kg={"seed": 1.0})) == 0  # a meal is the act itself
    assert cap.witnessed_salience(dict(base, act="eat:decayed_tissue", eaten_kg={"decayed_tissue": 0.1}, hurt=True)) == 1
    assert cap.witnessed_salience(dict(base, act="cut:fresh_tissue|stone_edged", eaten_kg={"fresh_tissue": 0.3}, exposed_kg=0.4)) == 2
    assert cap.witnessed_salience(dict(base, act="strike:animal_grazer|stick", killed=True, exposed_kg=0.05)) == 2
    assert cap.witnessed_salience(dict(base, act="strike:stone_small|stone_heavy", appeared=["stone_edged"], transformed=True)) == 2


def test_conspicuous_events_still_age_out_eventually():
    sc = Scenario(capacities=True)
    w = _witness(sc)
    flake = dict(_visible(0.0, created=["stone_edged"]), appeared=["stone_edged"], transformed=True)
    cap.observe_outcome(_ctx(sc, 0), "strike:stone_small|stone_heavy", visible=flake)
    # A salience-2 event is kept as if 60 days newer; routine events from later
    # than that push it out.
    _fill_with_meals(sc, w, cap.WITNESSED_MEMORY + 5, start=2 * cap.RETENTION_DAYS_PER_CONSEQUENCE + 1)
    assert "strike:stone_small|stone_heavy" not in [e["act"] for e in w["cognition"]["witnessed"]]


def test_picking_up_a_stone_is_not_new_matter_or_a_change_of_form():
    sc = Scenario(capacities=True)
    sc.add_stone(0, 0, "pebble")
    out = cap.execute(_ctx(sc), "grasp:stone_heavy|none", {"verb": "grasp_natural", "id": "pebble"})
    assert out["created_classes"]  # the object list gained it (unchanged step-1 field)
    assert out["appeared_classes"] == [] and out["transformed"] is False
