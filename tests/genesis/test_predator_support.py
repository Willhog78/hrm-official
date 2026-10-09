"""Reserve-backed reproductive support preserves episodic predator feeding."""
from copy import deepcopy

import pytest

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology import animals
from hrm_genesis.ecology.traits import scaled_life_history_ticks, trait_for
from tests.genesis.test_consumer_opportunity import _animal, _world
from qualification.genesis.tier_observer import build_config


def habitat(tpy=365, model="reserve-backed-v1", prey_count=12):
    c, p, m, w = _world(tpy, "elapsed-time-v2", 2)
    if model != "consecutive-feeding-legacy":
        c["predator_support_model"] = model
    predator = _animal("a-stalker", "stalker", 0, 0, 10.0)
    predator["age_ticks"] = scaled_life_history_ticks(trait_for("stalker").maturity_ticks, tpy)
    c["animals"] = [predator] + [_animal(f"z-prey-{i}", "browser", 0, 0, 50.0) for i in range(prey_count)]
    # Real, finite food and water. Ecology is isolated from climate/plant growth.
    for cell in p["cells"]:
        for s in cell["plant_elements_kg"]:
            cell["plant_elements_kg"][s] = 1000.0 * animals.PLANT_ELEMENT_FRACTIONS[s]
    return c, p, m, w


def run_habitat(tpy, model, ticks):
    c, p, m, w = habitat(tpy, model)
    first_meal = first_birth = None
    max_streak = 0
    for epoch in range(ticks):
        c, p, m = animals.evolve_consumers(c, p, m, w, epoch)
        parent = next((a for a in c["animals"] if a["id"] == "a-stalker"), None)
        if parent:
            if first_meal is None and parent["last_forage_success"] > 0.0:
                first_meal = epoch
            max_streak = max(max_streak, parent["support_streak"])
        if first_birth is None and any(a["species"] == "stalker" and a["generation"] == 1 for a in c["animals"]):
            first_birth = epoch
    return {"first_meal": first_meal, "first_birth": first_birth, "max_streak": max_streak, "state": c, "producers": p, "matter": m}


def test_real_intermittent_hunting_can_produce_offspring_without_daily_kills():
    fixed = run_habitat(365, "reserve-backed-v1", 4 * 365)
    old = run_habitat(365, "consecutive-feeding-legacy", 4 * 365)
    assert fixed["first_meal"] is not None
    assert fixed["first_birth"] is not None
    assert fixed["first_birth"] - fixed["first_meal"] + 1 >= 912
    assert old["first_birth"] is None
    assert old["max_streak"] <= 1


def test_support_requirement_represents_the_same_elapsed_duration():
    monthly = run_habitat(12, "reserve-backed-v1", 4 * 12)
    daily = run_habitat(365, "reserve-backed-v1", 4 * 365)
    assert monthly["first_birth"] is not None and daily["first_birth"] is not None
    monthly_duration = (monthly["first_birth"] - monthly["first_meal"] + 1) / 12
    daily_duration = (daily["first_birth"] - daily["first_meal"] + 1) / 365
    assert monthly_duration == pytest.approx(2.5)
    assert daily_duration == pytest.approx(2.5, abs=1/365)


def test_nonfeeding_day_keeps_meal_backed_support():
    c, p, m, w = habitat()
    c["animals"][0].update(energy=50.0, predator_last_meal_epoch=0, support_streak=10)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 1)
    parent = next(a for a in c["animals"] if a["id"] == "a-stalker")
    assert parent["last_forage_success"] == 0.0
    assert parent["support_streak"] == 11
    assert parent["energy"] < 50.0


def test_starting_energy_without_a_real_meal_does_not_create_support():
    c, p, m, w = habitat()
    c["animals"][0].update(energy=50.0, support_streak=911)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 1)
    parent = next(a for a in c["animals"] if a["id"] == "a-stalker")
    assert parent["support_streak"] == 0
    assert not any(a["species"] == "stalker" and a["generation"] > 0 for a in c["animals"])


def test_energy_shortfall_resets_support_without_free_food(monkeypatch):
    c, p, m, w = habitat(prey_count=0)
    c["animals"][0].update(energy=0.015, predator_last_meal_epoch=0, support_streak=100)
    monkeypatch.setattr(animals, "has_opportunity", lambda *a: False)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 1)
    parent = next(a for a in c["animals"] if a["id"] == "a-stalker")
    assert 0.0 < parent["energy"] < 0.30 * 12 / 365
    assert parent["support_streak"] == 0


def test_no_replacement_without_local_live_prey():
    c, p, m, w = habitat(prey_count=0)
    c["animals"][0].update(energy=50.0, predator_last_meal_epoch=0, support_streak=911)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 1)
    assert c["last_tick_births"] == 0
    assert c["animals"][0]["support_streak"] == 912


def test_eaten_prey_cannot_certify_replacement_habitat(monkeypatch):
    c, p, m, w = habitat(prey_count=1)
    c["animals"][0].update(energy=10.0, predator_last_meal_epoch=0, support_streak=911)
    monkeypatch.setattr(animals, "has_opportunity", lambda *a: True)
    monkeypatch.setattr(animals, "_hunt_succeeds", lambda *a: True)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 1)
    assert c["last_tick_deaths_by_cause"]["predation"] == 1
    assert c["last_tick_births"] == 0


def test_cooldown_still_blocks_birth_with_full_support():
    c, p, m, w = habitat()
    c["animals"][0].update(energy=50.0, predator_last_meal_epoch=0, support_streak=911, last_reproduction_epoch=0)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 1)
    assert c["last_tick_births"] == 0


def test_herbivores_and_legacy_states_are_unchanged():
    c, p, m, w = habitat()
    c["animals"] = [a for a in c["animals"] if a["species"] != "stalker"]
    legacy = deepcopy(c)
    del legacy["predator_support_model"]
    for epoch in range(30):
        c, pnew, mnew = animals.evolve_consumers(c, p, m, w, epoch)
        legacy, pold, mold = animals.evolve_consumers(legacy, p, m, w, epoch)
        assert c["animals"] == legacy["animals"]
        assert pnew == pold and mnew == mold
        p, m = pnew, mnew


def test_config_is_fingerprinted_and_default_checkpoint_shape_is_preserved():
    old = build_config("agentus-demography-c", "v1-remainingmilk")
    new = build_config("agentus-demography-c", "v1-remainingmilk-reservepredators")
    assert old.predator_support_model == "consecutive-feeding-legacy"
    assert "predator_support_model" not in old.canonical()
    assert new.canonical()["predator_support_model"] == "reserve-backed-v1"
    assert old.fingerprint() != new.fingerprint()
    assert "predator_support_model" not in GenesisSimulation(old).consumer_state()
    assert GenesisSimulation(new).consumer_state()["predator_support_model"] == "reserve-backed-v1"
    with pytest.raises(ValueError):
        GenesisConfig(predator_support_model="always-reproduce")


def test_immaturity_still_blocks_birth():
    c, p, m, w = habitat()
    c["animals"][0].update(energy=50.0, age_ticks=0, predator_last_meal_epoch=0, support_streak=911)
    c, _, _ = animals.evolve_consumers(c, p, m, w, 1)
    assert c["last_tick_births"] == 0


def test_real_predator_births_preserve_elements_and_water():
    from hrm_genesis.ecology.plants import ecology_element_totals
    from hrm_genesis.matter.pools import total_elements, total_water
    def totals(c, p, m):
        stocks = (animals.consumer_element_totals(c), ecology_element_totals(p), total_elements(m["cells"]))
        elements = {symbol: sum(stock.get(symbol, 0.0) for stock in stocks) for symbol in animals.ANIMAL_TRACKED_ELEMENTS}
        water = animals.consumer_water_total_kg(c) + total_water(m["cells"]) + m.get("water_output_kg", 0.0)
        return elements, water
    c, p, m, _ = habitat()
    initial_elements, initial_water = totals(c, p, m)
    result = run_habitat(365, "reserve-backed-v1", 4 * 365)
    assert result["first_birth"] is not None
    final_elements, final_water = totals(result["state"], result["producers"], result["matter"])
    assert final_elements == pytest.approx(initial_elements, abs=1e-5)
    assert final_water == pytest.approx(initial_water, abs=1e-6)
