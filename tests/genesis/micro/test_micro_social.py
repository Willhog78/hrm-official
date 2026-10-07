"""MICRO: social learning carries only what bodies and the world show (G10.7a).

An observer may see an act (verb and object classes) and what visibly
followed: food eaten, objects appearing, the actor hurt. It never receives the
actor's reward or the eater's energy yield, and food value still comes only
from its own eating.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _scenario import Scenario
from hrm_genesis.human import interactions as cap
from hrm_genesis.human.communication import G7_LEGACY, imitate_signal, signal_sequence
from hrm_genesis.human.diet import innate_food_prior

KEY = "cut:fresh_tissue|stone_edged"


def _ctx(sc: Scenario, epoch: int = 3) -> cap.Context:
    xy = sc.xy
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == xy)
    return cap.Context(sc.humans, sc.agent, dict(sc.profile, development_scale=1.0), pcell, sc.carcass(*xy),
                       sc.matter["lithic_cells"], {"precipitation": 0.0}, sc.consumers, epoch)


def _watchers(sc: Scenario, *values: float | None):
    out = []
    for n, v in enumerate(values):
        w = sc.add_agent(f"watcher-{n}", 0, 0)
        w["cognition"]["food_values"] = innate_food_prior(sc.profile)
        if v is not None:
            w["cognition"]["food_values"]["fresh_tissue"] = v
        out.append(w)
    return out


def _seen_eating(kg: float = 0.5, injury: float = 0.0, created=()):
    return {"eaten_kg": {"fresh_tissue": kg} if kg else {}, "created": list(created), "injury": injury}


def test_the_actors_reward_never_reaches_an_observer():
    sc = Scenario(capacities=True)
    naive, = _watchers(sc, None)
    cap.observe_outcome(_ctx(sc), KEY, reward=50.0, visible=_seen_eating())
    assert KEY not in naive["cognition"]["affordance_values"], "a naive observer valued meat it has never eaten"


def test_observers_appraise_the_same_event_by_their_own_food_values():
    sc = Scenario(capacities=True)
    low, high = _watchers(sc, 500.0, 4000.0)
    for reward in (0.01, 99.0):  # the actor's own reward must make no difference
        for w in (low, high):
            w["cognition"]["affordance_values"] = {}
        cap.observe_outcome(_ctx(sc), KEY, reward=reward, visible=_seen_eating(0.5))
        v_low = low["cognition"]["affordance_values"][KEY]["v"]
        v_high = high["cognition"]["affordance_values"][KEY]["v"]
        assert 0.0 < v_low < v_high
        expected_high = cap.OBSERVATION_RATE * 4000.0 * 0.5 / float(sc.profile["basal_energy_kcal_per_tick"])
        assert v_high == pytest.approx(expected_high, rel=1e-6)


def test_a_visibly_hurt_actor_teaches_caution():
    sc = Scenario(capacities=True)
    w, = _watchers(sc, None)
    cap.observe_outcome(_ctx(sc), "strike:animal_grazer|none", visible=_seen_eating(0.0, injury=0.1))
    assert w["cognition"]["affordance_values"]["strike:animal_grazer|none"]["v"] < 0.0


def test_an_appearing_object_matters_only_to_an_observer_that_has_used_such_objects():
    sc = Scenario(capacities=True)
    novice, user = _watchers(sc, None, None)
    user["cognition"]["affordance_values"] = {"cut:fresh_tissue|stone_edged": {"n": 3, "v": 0.6}}
    key = "strike:stone_small|stone_heavy"
    cap.observe_outcome(_ctx(sc), key, visible=_seen_eating(0.0, created=["stone_edged"]))
    assert key not in novice["cognition"]["affordance_values"]
    assert user["cognition"]["affordance_values"][key]["v"] > 0.0


def test_observers_in_other_cells_see_nothing():
    sc = Scenario(capacities=True)
    far = sc.add_agent("far", 3, 0)
    far["cognition"]["food_values"]["fresh_tissue"] = 4000.0
    cap.observe_outcome(_ctx(sc), KEY, visible=_seen_eating())
    cap.observe_food(_ctx(sc), [{"kind": "seed", "kg": 1.0, "kcal": 2850.0, "hazard": 0.0, "handling_kcal": 60.0}])
    assert KEY not in far["cognition"]["affordance_values"]
    assert "observed_ingestion" not in far["cognition"]


def test_seeing_food_eaten_transfers_no_energy_value():
    sc = Scenario(capacities=True)
    w, = _watchers(sc, None)
    cap.observe_food(_ctx(sc), [{"kind": "seed", "kg": 1.0, "kcal": 2850.0, "hazard": 0.0, "handling_kcal": 60.0}])
    assert "seed" not in w["cognition"]["food_values"]
    assert w["cognition"]["observed_ingestion"]["seed"] == {"harmless": 1, "harmful": 0}


def test_seen_harmless_eating_makes_tasting_likelier_and_seen_distress_prevents_it():
    sc = Scenario(capacities=True)
    pcell = next(c for c in sc.producers["cells"] if (c["x"], c["y"]) == (0, 0))
    sc.set_pool(0, 0, "seed_elements_kg", 50.0)
    agent = sc.agent
    agent["cognition"]["food_values"] = innate_food_prior(sc.profile)

    def tastes(seen):
        if seen is None:
            agent["cognition"].pop("observed_ingestion", None)
        else:
            agent["cognition"]["observed_ingestion"] = seen
        return sum(cap.choose_food_samples(agent, pcell, sc.carcass(0, 0), e, hungry=False) == ("seed",) for e in range(400))

    unseen = tastes(None)
    encouraged = tastes({"seed": {"harmless": 2, "harmful": 0}})
    deterred = tastes({"seed": {"harmless": 0, "harmful": 1}})
    assert encouraged > 2 * unseen and deterred == 0


def test_value_still_comes_only_from_the_observer_eating_it():
    sc = Scenario(capacities=True)
    agent = sc.agent
    agent["cognition"]["food_values"] = innate_food_prior(sc.profile)
    agent["cognition"]["observed_ingestion"] = {"seed": {"harmless": 3, "harmful": 0}}
    sc.set_pool(0, 0, "seed_elements_kg", 200.0)
    sc.set_water(0, 0, 50000.0)
    for _ in range(60):
        sc.step()
        if "seed" in sc.agent["cognition"]["food_values"]:
            break
    assert "seed" in sc.agent["cognition"]["food_values"], "never tasted a kind it saw eaten safely"
    assert sc.humans["capacity_stats"]["food_learned_after_observation"]["seed"] == 1
    assert sc.humans["capacity_stats"]["intake_kg_by_kind"]["seed"] > 0.0  # it ate it


def test_g7_recipe_transfer_is_unavailable_without_the_legacy_flag():
    teacher, learner = {"id": "t"}, {"id": "l"}
    with pytest.raises(ValueError):
        signal_sequence(teacher, ["grasp", "carry"])
    with pytest.raises(ValueError):
        imitate_signal(learner, {"sender_id": "t", "primitive_sequence": ["grasp"]})
    legacy = imitate_signal(learner, signal_sequence(teacher, ["grasp"], compatibility=G7_LEGACY), compatibility=G7_LEGACY)
    assert legacy["learned_sequences"] == [["grasp"]]


def test_no_live_module_uses_the_recipe_channel():
    src = Path(__file__).resolve().parents[3] / "src" / "hrm_genesis"
    users = [p.name for p in src.rglob("*.py") if p.name != "communication.py"
             and ("signal_sequence" in p.read_text() or "imitate_signal" in p.read_text())]
    assert users == []


def test_g10_4_legacy_observation_is_reproduced_with_the_flag():
    sc = Scenario(capacities=True, observation="g10.4-legacy")
    w = sc.add_agent("w", 0, 0)
    w["cognition"]["food_values"] = innate_food_prior(sc.profile)
    cap.observe_food(_ctx(sc), [{"kind": "seed", "kg": 1.0, "kcal": 2850.0, "hazard": 0.0, "handling_kcal": 60.0}])
    assert w["cognition"]["food_values"]["seed"] == pytest.approx(cap.OBSERVATION_RATE * 2850.0)
    cap.observe_outcome(_ctx(sc), KEY, reward=0.4)
    assert w["cognition"]["affordance_values"][KEY]["v"] == pytest.approx(0.2)
