"""Movement and encounter opportunities follow elapsed time (consumer timebase v2).

Under "elapsed-time-v2" an animal has one movement opportunity, one hunt
opportunity and one attack opportunity per reference tick (month) of elapsed
time. At 12 ticks/year that is every tick, exactly as before; at 365 ticks/year
it is a per-tick chance of 12/365. "elapsed-time-v1" (D2, rates only) keeps one
of each per tick. Each test isolates one opportunity in fixed conditions.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

import hrm_genesis.ecology.animals as animals
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import ANIMAL_TRACKED_ELEMENTS, evolve_consumers
from hrm_genesis.ecology.plants import PLANT_ELEMENT_FRACTIONS
from hrm_genesis.ecology.traits import (
    CONSUMER_TIMEBASE_ELAPSED as V1,
    CONSUMER_TIMEBASE_ELAPSED_V2 as V2,
    CONSUMER_TIMEBASE_LEGACY as LEGACY,
    has_opportunity,
    opportunity_draw,
    opportunity_probability,
    trait_for,
)
from hrm_genesis.human.biology import _apply_predator_threat


def _animal(aid: str, species: str, x: int, y: int, energy: float) -> dict:
    t = trait_for(species)
    return {"id": aid, "species": species, "x": x, "y": y, "age_ticks": 0, "energy": energy,
            "body_elements_kg": {s: t.adult_body_mass_kg * 0.6 * PLANT_ELEMENT_FRACTIONS[s] for s in ANIMAL_TRACKED_ELEMENTS},
            "body_water_kg": t.water_capacity_kg, "forage_bias": 0.0, "last_forage_success": 0.0,
            "support_streak": 0, "generation": 0, "last_reproduction_epoch": -1000000}


def _world(tpy: int, timebase: str, width: int, height: int = 2):
    sim = GenesisSimulation(GenesisConfig(
        master_seed="opportunity", world_width=width, world_height=height, ticks_per_year=tpy,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, consumer_timebase=timebase))
    consumers, producers, matter, world = (deepcopy(sim.consumer_state()), deepcopy(sim.ecology_state()),
                                           deepcopy(sim.matter_state()), deepcopy(sim.world_state()))
    for cell in producers["cells"]:
        for pool in ("plant_elements_kg", "seed_elements_kg"):
            for s in cell[pool]:
                cell[pool][s] = 0.0
    for cell in matter["cells"]:
        cell["surface_water_kg"] = 50.0
    consumers["animals"] = []
    return consumers, producers, matter, world


# -- the rule itself ------------------------------------------------------------

def test_probability_is_one_at_the_reference_timebase_and_for_earlier_timebases():
    assert opportunity_probability(12, V2) == 1.0
    assert opportunity_probability(365, V1) == 1.0
    assert opportunity_probability(365, LEGACY) == 1.0
    assert opportunity_probability(365, V2) == pytest.approx(12 / 365)
    assert opportunity_probability(6, V2) == 1.0  # capped: at most one per tick


def test_draws_are_deterministic_and_occur_at_the_declared_rate():
    assert opportunity_draw("a", 3, "move") == opportunity_draw("a", 3, "move")
    n = 60000
    hits = sum(has_opportunity(365, V2, f"animal-{i % 50}", i, "move") for i in range(n))
    p = 12 / 365
    assert abs(hits - n * p) < 4 * (n * p * (1 - p)) ** 0.5


# -- one animal, one opportunity --------------------------------------------------

def _steps_toward_richer_food(tpy: int, timebase: str, years: int) -> int:
    """A grazer on a strip where the next cell east is always richer wants to
    move every tick (each cell east holds 0.2 kg more, above the 0.081 distance
    cost in its destination score); count the cells it actually moves."""
    width = 90
    consumers, producers, matter, world = _world(tpy, timebase, width)
    for cell in producers["cells"]:
        for s in cell["plant_elements_kg"]:
            cell["plant_elements_kg"][s] = 0.2 * (1 + int(cell["x"])) * PLANT_ELEMENT_FRACTIONS[s]
    consumers["animals"] = [_animal("grazer-m", "grazer", 0, 0, 30.0)]
    steps = 0
    for epoch in range(tpy * years):
        x0 = consumers["animals"][0]["x"] if consumers["animals"] else None
        consumers, producers, matter = evolve_consumers(consumers, producers, matter, world, epoch)
        if not consumers["animals"]:
            break
        steps += abs(int(consumers["animals"][0]["x"]) - int(x0))
    return steps


def test_movement_per_simulated_year_matches_the_reference_timebase():
    years = 5
    monthly = _steps_toward_richer_food(12, V2, years)
    daily_v2 = _steps_toward_richer_food(365, V2, years)
    daily_v1 = _steps_toward_richer_food(365, V1, years)
    assert monthly == 12 * years
    # Binomial(1825, 12/365): mean 60, sd about 7.6.
    assert 35 <= daily_v2 <= 85
    # One step per tick: the strip's 89 cells are crossed within the first months.
    assert daily_v1 >= 85


def _hunt_attempts(tpy: int, timebase: str, monkeypatch) -> int:
    """A hungry predator shares a cell with prey it never catches; count attempts in a year."""
    consumers, producers, matter, world = _world(tpy, timebase, 2)
    for cell in matter["cells"]:
        cell["surface_water_kg"] = 50.0
    consumers["animals"] = [_animal("stalker-h", "stalker", 0, 0, 12.0), _animal("browser-p", "browser", 0, 0, 30.0)]
    attempts = []
    monkeypatch.setattr(animals, "_hunt_succeeds", lambda predator, prey, epoch: attempts.append(epoch) or False)
    for epoch in range(tpy):
        consumers, producers, matter = evolve_consumers(consumers, producers, matter, world, epoch)
        if not any(a["species"] == "stalker" for a in consumers["animals"]):
            break
    return len(attempts)


def test_hunt_attempts_per_simulated_year_match_the_reference_timebase(monkeypatch):
    monthly = _hunt_attempts(12, V2, monkeypatch)
    daily_v2 = _hunt_attempts(365, V2, monkeypatch)
    daily_v1 = _hunt_attempts(365, V1, monkeypatch)
    assert monthly == 12
    assert 3 <= daily_v2 <= 25  # Binomial(365, 12/365): mean 12, sd about 3.4
    # One attempt per tick, each costing energy, until the predator starves.
    assert daily_v1 >= 40


def test_predator_attacks_on_agentus_per_simulated_year_match_the_reference_timebase():
    human = {"id": "human-t", "x": 0, "y": 0, "injury": 0.0,
             "body_elements_kg": {"C": 20.0}, "body_water_kg": 40.0}
    predator = _animal("stalker-a", "stalker", 0, 0, 5.0)  # hungry: below 2x reproduction energy

    def attacks(tpy: int, timebase: str) -> int:
        state = {"ticks_per_year": tpy, "animals": [predator]}
        if timebase != LEGACY:
            state["rate_timebase"] = timebase
        total = 0
        for epoch in range(tpy):
            h = dict(human)
            total += _apply_predator_threat(h, state, epoch)
        return total

    assert attacks(12, V2) == 12
    assert 3 <= attacks(365, V2) <= 25
    assert attacks(365, V1) == 365
    assert attacks(365, LEGACY) == 365


def test_monthly_and_earlier_timebase_fingerprints_are_unchanged():
    base = dict(master_seed="fp", producer_ecology_enabled=True, consumer_ecology_enabled=True)
    assert "consumer_timebase" not in GenesisConfig(ticks_per_year=12, **base).canonical()
    assert GenesisConfig(ticks_per_year=365, **base).canonical()["consumer_timebase"] == V2
    assert GenesisConfig(ticks_per_year=365, consumer_timebase=V1, **base).canonical()["consumer_timebase"] == V1
    assert "consumer_timebase" not in GenesisConfig(ticks_per_year=365, consumer_timebase=LEGACY, **base).canonical()
