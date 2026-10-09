"""Pairing identity is persistent metadata, not privileged kinship knowledge."""
from copy import deepcopy
from dataclasses import replace

import pytest

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human import biology
from hrm_genesis.human.lineage import (
    PARENTAGE_MODEL, ancestor_ids, enable_parentage, record_birth,
    record_death, recorded_relationship,
)
from hrm_genesis.human.perception import perceive_local
from qualification.genesis.tier_observer import build_config


def strip_parentage(state):
    state = deepcopy(state)
    state.pop("parentage_model", None)
    state.pop("lineage", None)
    for person in state["humans"]:
        for field in ("mother_id", "father_id", "birth_epoch"):
            person.pop(field, None)
    return state


def contact_world(monkeypatch, scenario="contact", tracking=True):
    config = GenesisConfig(
        master_seed="reproduction-contact", world_width=4, world_height=4,
        producer_ecology_enabled=True, consumer_ecology_enabled=True,
        human_biology_enabled=True, human_calibration_enabled=True,
        ticks_per_year=365, material_scale_factor=1000.0,
    )
    sim = GenesisSimulation(config)
    state = sim.human_state()
    mother, father = state["humans"]
    for person in state["humans"]:
        person["x"], person["y"] = 1, 1
        person["energy"] = 20000.0
    destinations = {p["id"]: (1, 1) for p in state["humans"]}
    if scenario == "departed":
        destinations[father["id"]] = (2, 1)
    elif scenario == "arrived":
        mother["x"], father["x"] = 0, 2
    elif scenario == "dead":
        father["energy"] = -10000.0
    elif scenario == "immature":
        father["age_ticks"] = int(state["physiology_profile"]["maturity_ticks"]) - 2
    elif scenario == "multiple":
        other = deepcopy(father)
        other["id"] = "human-a-eligible"
        state["humans"].append(other)
        destinations[other["id"]] = (1, 1)
    if tracking:
        enable_parentage(state)
    monkeypatch.setattr(biology, "_move_toward_food", lambda p, producers: destinations[p["id"]])
    result, producers, matter = biology.evolve_humans(
        state, sim.ecology_state(), sim.matter_state(), sim.world_state(), 1,
    )
    return result, producers, matter


@pytest.mark.parametrize("scenario,births", [
    ("contact", 1), ("arrived", 1), ("departed", 0), ("dead", 0), ("immature", 0),
])
def test_pairing_uses_only_living_mature_males_after_movement(monkeypatch, scenario, births):
    on, p_on, m_on = contact_world(monkeypatch, scenario)
    off, p_off, m_off = contact_world(monkeypatch, scenario, tracking=False)
    assert strip_parentage(on) == off
    assert (p_on, m_on) == (p_off, m_off)
    assert on["cumulative_births"] == births
    newborns = [p for p in on["humans"] if p["age_ticks"] == 0]
    if births:
        child = newborns[0]
        assert child["mother_id"] == "human-g00000000"
        assert child["father_id"] == "human-g00000001"
        assert child["birth_epoch"] == 1
        assert child["caregiver_id"] == child["mother_id"]
        assert on["lineage"][child["id"]]["candidate_father_ids"] == [child["father_id"]]
    else:
        assert len(on["lineage"]) == 2
    if scenario == "dead":
        assert on["lineage"]["human-g00000001"]["death_epoch"] == 1
        assert all(p["id"] != "human-g00000001" for p in on["humans"])


def test_multiple_candidates_use_stable_id_pairing(monkeypatch):
    state, _, _ = contact_world(monkeypatch, "multiple")
    child = next(p for p in state["humans"] if p["age_ticks"] == 0)
    assert child["father_id"] == "human-a-eligible"
    assert state["lineage"][child["id"]]["candidate_father_ids"] == [
        "human-a-eligible", "human-g00000001",
    ]


def register():
    state = {"humans": [
        {"id": pid, "sex": sex, "generation": 0}
        for pid, sex in (("m", "female"), ("f", "male"), ("x", "male"), ("y", "female"))
    ]}
    enable_parentage(state)
    people = {p["id"]: p for p in state["humans"]}
    for pid, mother, father in (("daughter", "m", "f"), ("son", "m", "f"),
                               ("half", "y", "f"), ("grandchild", "daughter", "x")):
        child = {"id": pid, "sex": "male", "generation": people[mother]["generation"] + 1}
        record_birth(state, child, people[mother], [people[father]], 10)
        people[pid] = child
    return state, people


def test_both_sides_of_ancestry_survive_death_and_json_roundtrip():
    import json
    state, _ = register()
    record_death(state, "f", 11)
    restored = json.loads(json.dumps(state))
    assert ancestor_ids(restored["lineage"], "grandchild") == {"daughter", "x", "m", "f"}
    assert restored["lineage"]["f"]["death_epoch"] == 11
    assert recorded_relationship(restored["lineage"], "grandchild", "f") == "ancestor_descendant"


def test_relationships_include_paternal_half_siblings_and_unknown_founders():
    state, _ = register()
    records = state["lineage"]
    assert recorded_relationship(records, "daughter", "son") == "full_siblings"
    assert recorded_relationship(records, "daughter", "half") == "half_siblings"
    assert recorded_relationship(records, "grandchild", "half") == "shared_ancestry"
    assert recorded_relationship(records, "m", "son") == "parent_child"
    assert recorded_relationship(records, "m", "x") == "no_recorded_relation"
    assert recorded_relationship(records, "missing", "x") == "unknown_record"
    assert recorded_relationship(records, "son", "son") == "self"
    assert records["m"]["birth_epoch"] is None


def test_related_pair_is_recorded_without_blocking_birth():
    state, people = register()
    child = {"id": "related-child", "sex": "female", "generation": 1}
    record_birth(state, child, people["m"], [people["son"]], 20)
    assert child["father_id"] == "son"
    assert state["lineage"][child["id"]]["parent_relationship"] == "parent_child"
    assert ancestor_ids(state["lineage"], child["id"]) == {"m", "f", "son"}


def test_reassigned_caregiver_does_not_rewrite_biological_parents():
    state, people = register()
    child = people["grandchild"]
    child.update(x=1, y=1, caregiver_id="dead", population_id="a")
    adoptive = {"id": "adoptive", "x": 1, "y": 1, "age_ticks": 9999}
    before = deepcopy(state["lineage"])
    assert biology._resolve_caregiver(child, {"adoptive": adoptive}, {
        "caregiver_dependence": 1.0, "maturity_ticks": 6570,
    }) is adoptive
    assert child["caregiver_id"] == "adoptive"
    assert child["mother_id"] == "daughter" and child["father_id"] == "x"
    assert state["lineage"] == before


def test_ancestry_traversal_handles_unknown_and_cyclic_input():
    records = {"a": {"mother_id": "b", "father_id": "missing"}, "b": {"mother_id": "a"}}
    assert ancestor_ids(records, "a") == {"b", "missing"}
    assert ancestor_ids(records, "unknown") == set()


def test_empty_pairing_cannot_silently_invent_paternity():
    state, people = register()
    with pytest.raises(ValueError, match="eligible male"):
        record_birth(state, {"id": "child"}, people["m"], [], 1)


def test_config_defaults_and_fingerprints_remain_compatible():
    old = build_config("agentus-demography-a", "v1-remainingmilk-reservepredators-searchpredators")
    on = build_config("agentus-demography-a", "v1-remainingmilk-reservepredators-searchpredators-parentage")
    assert old.agentus_parentage_model == "none"
    assert "agentus_parentage_model" not in old.canonical()
    assert on.canonical() == {**old.canonical(), "agentus_parentage_model": PARENTAGE_MODEL}
    assert on.fingerprint() != old.fingerprint()
    assert replace(GenesisConfig(), agentus_parentage_model=PARENTAGE_MODEL).fingerprint() == GenesisConfig().fingerprint()
    with pytest.raises(ValueError, match="parentage"):
        GenesisConfig(agentus_parentage_model="invented")


def test_perception_has_no_parentage_or_global_lineage_knowledge(monkeypatch):
    on, producers, matter = contact_world(monkeypatch)
    plain = strip_parentage(on)
    for i, person in enumerate(on["humans"]):
        assert perceive_local(person, producers, matter, on["humans"]) == perceive_local(
            plain["humans"][i], producers, matter, plain["humans"],
        )


def test_canonical_checkpoint_and_replay_preserve_lineage(tmp_path):
    config = GenesisConfig(
        master_seed="parentage-checkpoint", world_width=8, world_height=8,
        producer_ecology_enabled=True, consumer_ecology_enabled=True,
        human_biology_enabled=True, agentus_parentage_model=PARENTAGE_MODEL,
    )
    uninterrupted = GenesisSimulation(config)
    uninterrupted.run(120)
    split = GenesisSimulation(config)
    split.run(45)
    assert split.human_state()["cumulative_births"] > 0
    path = tmp_path / "parentage.json"
    split.write_checkpoint(path)
    restored = GenesisSimulation.load_checkpoint(path, config)
    restored.run(75)
    assert restored.snapshot() == uninterrupted.snapshot()
    assert restored.human_state()["cumulative_births"] > 0
    assert len(restored.human_state()["lineage"]) == 2 + restored.human_state()["cumulative_births"]
    assert restored.ledger.verify_chain()
    with pytest.raises(ValueError, match="fingerprint"):
        GenesisSimulation.load_checkpoint(path, replace(config, agentus_parentage_model="none"))
