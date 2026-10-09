"""Family allocation regressions for opt-in remaining-demand-v2."""
import pytest

from _scenario import Scenario, el
from hrm_genesis.human import biology as bio
from qualification.genesis.tier_observer import build_config


def family(model, food=50000.0):
    sc = Scenario(capacities=True, width=3)
    sc.humans["nursing_model"] = model
    mother = sc.set_agent(0, 0, sex="female", energy=250.0)
    mother["last_reproduction_epoch"] = sc.epoch
    sc.set_pool(0, 0, "plant_elements_kg", food)
    sc.set_water(0, 0, 50000.0)
    for aid, age in (("human-b00000001", 1460), ("human-b00000002", 1095),
                     ("human-b00000003", 730), ("human-b00000004", 365),
                     ("human-b00000005", 40)):
        scale = 0.05 + 0.95 * age / (18 * 365)
        sc.add_agent(aid, 0, 0, sex="male", age_ticks=age,
                     caregiver_id=mother["id"], energy=200.0, generation=1,
                     body_elements_kg=el(28.0 * scale), body_water_kg=42.0 * scale)
    return sc


def trace_day(sc, monkeypatch):
    calls = []
    original = bio._provision_dependent
    def record(child, caregiver, profile, *args, **kwargs):
        c0 = float(child["energy"])
        m0 = None if caregiver is None else float(caregiver["energy"])
        result = original(child, caregiver, profile, *args, **kwargs)
        if caregiver is not None:
            calls.append({"id": child["id"], "age": child["age_ticks"],
                          "before": c0, "milk": float(child["energy"]) - c0,
                          "cost": m0 - float(caregiver["energy"])})
        return result
    monkeypatch.setattr(bio, "_provision_dependent", record)
    sc.step()
    return calls


def test_infant_gets_priority_and_solids_reduce_older_siblings_milk(monkeypatch):
    old = trace_day(family(bio.NURSING_DEMAND_LIMITED), monkeypatch)
    monkeypatch.undo()
    new = trace_day(family(bio.NURSING_REMAINING_DEMAND), monkeypatch)
    assert [r["age"] for r in old] == [1460, 1095, 730, 365, 40]
    assert [r["age"] for r in new] == [40, 365, 730, 1095, 1460]
    old_infant = next(r for r in old if r["age"] == 40)
    new_infant = next(r for r in new if r["age"] == 40)
    assert old_infant["milk"] < 200.0
    assert new_infant["milk"] >= 200.0
    assert sum(r["milk"] for r in new if r["age"] >= 180) < sum(r["milk"] for r in old if r["age"] >= 180)
    assert all(r["cost"] == pytest.approx(r["milk"]) for r in new)


def test_fixed_scarce_family_keeps_infant_alive_without_free_energy():
    outcomes = {}
    for model in (bio.NURSING_DEMAND_LIMITED, bio.NURSING_REMAINING_DEMAND):
        sc = family(model)
        for _ in range(150):
            sc.set_pool(0, 0, "plant_elements_kg", 50000.0)
            sc.set_water(0, 0, 50000.0)
            sc.step()
        outcomes[model] = sc
    assert any(d["id"] == "human-b00000005" for d in outcomes[bio.NURSING_DEMAND_LIMITED].deaths())
    fixed = outcomes[bio.NURSING_REMAINING_DEMAND]
    assert any(h["id"] == "human-b00000005" for h in fixed.humans["humans"])
    stats = fixed.humans["nursing_stats"]
    assert stats["milk_absorbed_kcal"] == pytest.approx(stats["milk_produced_kcal"])
    assert stats["milk_cost_kcal"] == pytest.approx(stats["milk_absorbed_kcal"])
    assert stats["milk_unabsorbed_kcal"] == pytest.approx(0.0, abs=1e-9)


def test_no_food_still_limits_milk_to_mothers_actual_energy(monkeypatch):
    records = trace_day(family(bio.NURSING_REMAINING_DEMAND, food=0.0), monkeypatch)
    assert sum(r["milk"] for r in records) <= 50.0 + 1e-9
    assert all(r["cost"] == pytest.approx(r["milk"]) for r in records)


def test_new_model_is_fingerprinted_and_old_default_is_preserved():
    old = build_config("agentus-demography-b", "v1")
    new = build_config("agentus-demography-b", "v1-remainingmilk")
    assert old.nursing_model == bio.NURSING_DEMAND_LIMITED
    assert new.nursing_model == bio.NURSING_REMAINING_DEMAND
    assert new.canonical()["agentus_nursing"] == bio.NURSING_REMAINING_DEMAND
    assert old.fingerprint() != new.fingerprint()
    assert {k: v for k, v in old.canonical().items() if k != "agentus_nursing"} == {k: v for k, v in new.canonical().items() if k != "agentus_nursing"}


@pytest.mark.parametrize("physiology", ["reference-v1", "reference-v2"])
def test_new_model_pays_conversion_cost_and_respects_the_child_store(physiology):
    sc = Scenario(capacities=True, physiology=physiology)
    mother = sc.set_agent(0, 0, sex="female", energy=60000.0)
    infant = sc.add_agent("infant", 0, 0, age_ticks=60, caregiver_id=mother["id"])
    profile = bio._age_profile(infant, sc.profile)
    capacity = bio.energy_store_capacity(profile)
    infant["energy"] = capacity - 50.0
    before = mother["energy"]
    stats = {}
    bio._provision_dependent(infant, mother, profile, bio.NURSING_REMAINING_DEMAND, stats)
    assert infant["energy"] == pytest.approx(capacity)
    assert before - mother["energy"] == pytest.approx(50.0 / profile.get("lactation_efficiency", 1.0))
    assert stats["milk_absorbed_kcal"] == pytest.approx(50.0)
    assert stats["milk_cost_kcal"] == pytest.approx(stats["milk_absorbed_kcal"] + stats["milk_conversion_heat_kcal"])


def test_solids_can_fill_the_child_store_without_requesting_milk(monkeypatch):
    sc = family(bio.NURSING_REMAINING_DEMAND)
    older = next(h for h in sc.humans["humans"] if h["age_ticks"] == 1460)
    profile = bio._age_profile(older, sc.profile)
    older["energy"] = bio.energy_store_capacity(profile) - 50.0
    records = trace_day(sc, monkeypatch)
    rec = next(r for r in records if r["age"] == 1460)
    assert rec["milk"] == pytest.approx(0.0)
    assert rec["cost"] == pytest.approx(0.0)
