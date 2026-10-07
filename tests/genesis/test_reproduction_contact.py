from copy import deepcopy

import pytest

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.human import biology


def test_orphan_can_find_nearby_adult_across_population_labels():
    child = {"id": "child", "x": 1, "y": 1, "population_id": "population-1", "caregiver_id": "dead"}
    adult = {"id": "adult", "x": 2, "y": 1, "population_id": "population-2", "age_ticks": 7000}
    profile = {"caregiver_dependence": 1.0, "maturity_ticks": 6570}
    assert biology._resolve_caregiver(child, {"adult": adult}, profile) is adult
    assert child["caregiver_id"] == "adult"
    adult["x"] = 3
    child["caregiver_id"] = "dead"
    assert biology._resolve_caregiver(child, {"adult": adult}, profile) is None


@pytest.mark.parametrize("scenario,expected", [
    ("departed", 0), ("arrived", 1), ("dead_partner", 0), ("immature", 0),
])
def test_birth_requires_living_adult_contact_after_movement(monkeypatch, scenario, expected):
    sim = GenesisSimulation(GenesisConfig(
        master_seed="reproduction-contact", world_width=4, world_height=4,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, human_biology_enabled=True,
        human_calibration_enabled=True, ticks_per_year=365,
        material_scale_factor=1000.0,
    ))
    state = sim.human_state()
    female, male = state["humans"]
    for person in state["humans"]:
        person["x"], person["y"] = 1, 1
        person["energy"] = 20000.0
    destinations = {female["id"]: (1, 1), male["id"]: (1, 1)}
    if scenario == "departed":
        destinations[male["id"]] = (2, 1)
    elif scenario == "arrived":
        female["x"], male["x"] = 0, 2
    elif scenario == "dead_partner":
        male["energy"] = -10000.0
    elif scenario == "immature":
        # A young female must not borrow another female's adult eligibility.
        adult = deepcopy(female)
        adult["id"] = "human-g00000002"
        adult["last_reproduction_epoch"] = 0
        state["humans"].append(adult)
        destinations[adult["id"]] = (1, 1)
        female["age_ticks"] = int(state["physiology_profile"]["maturity_ticks"]) - 2
    monkeypatch.setattr(biology, "_move_toward_food", lambda human, producers: destinations[human["id"]])
    result, _, _ = biology.evolve_humans(
        state, sim.ecology_state(), sim.matter_state(), sim.world_state(), 1,
    )
    assert result["cumulative_births"] == expected
