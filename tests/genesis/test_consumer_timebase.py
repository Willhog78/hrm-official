"""Consumer rates follow elapsed time, not tick count (D2 units correction).

Trait rates are stated per month (12 ticks/year). Under "elapsed-time-v1" a
simulated year must cost and yield the same at 12 and at 365 ticks/year;
"per-tick-legacy" keeps the old behaviour, about 30x more per year at daily
ticks. Each test isolates one animal and one rate in fixed conditions.
"""

from __future__ import annotations

import math
from copy import deepcopy

import pytest

from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology.animals import ANIMAL_TRACKED_ELEMENTS, evolve_consumers
from hrm_genesis.ecology.plants import PLANT_ELEMENT_FRACTIONS
from hrm_genesis.ecology.traits import (
    CONSUMER_TIMEBASE_ELAPSED,
    CONSUMER_TIMEBASE_LEGACY,
    per_tick_amount,
    per_tick_fraction,
    scaled_ticks,
    trait_for,
)

ELAPSED, LEGACY = CONSUMER_TIMEBASE_ELAPSED, CONSUMER_TIMEBASE_LEGACY


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def _world(ticks_per_year: int, timebase: str):
    """A 2x2 world with no plants, no water, no carcasses and one grazer at (0, 0)."""
    sim = GenesisSimulation(GenesisConfig(
        master_seed="timebase", world_width=2, world_height=2, ticks_per_year=ticks_per_year,
        producer_ecology_enabled=True, consumer_ecology_enabled=True, consumer_timebase=timebase))
    consumers, producers, matter, world = (deepcopy(sim.consumer_state()), deepcopy(sim.ecology_state()),
                                           deepcopy(sim.matter_state()), deepcopy(sim.world_state()))
    for cell in producers["cells"]:
        for pool in ("plant_elements_kg", "seed_elements_kg"):
            for s in cell[pool]:
                cell[pool][s] = 0.0
    for cell in matter["cells"]:
        cell["surface_water_kg"] = 0.0
        cell["soil_water_kg"] = 0.0
    for cell in consumers["carcass_cells"]:
        cell["water_kg"] = 0.0
        for pool in ("elements_kg", "fresh_elements_kg"):
            for s in cell.get(pool, {}):
                cell[pool][s] = 0.0
    traits = trait_for("grazer")
    consumers["animals"] = [{
        "id": "grazer-t", "species": "grazer", "x": 0, "y": 0, "age_ticks": 0, "energy": 10.0,
        "body_elements_kg": {s: traits.adult_body_mass_kg * 0.5 * PLANT_ELEMENT_FRACTIONS[s] for s in ANIMAL_TRACKED_ELEMENTS},
        "body_water_kg": traits.water_capacity_kg, "forage_bias": 0.0, "last_forage_success": 0.0,
        "support_streak": 0, "generation": 0, "last_reproduction_epoch": -1000000,
    }]
    return consumers, producers, matter, world


def _run_year(ticks_per_year: int, timebase: str, setup=None):
    consumers, producers, matter, world = _world(ticks_per_year, timebase)
    if setup is not None:
        setup(consumers, producers, matter)
    for epoch in range(ticks_per_year):
        consumers, producers, matter = evolve_consumers(consumers, producers, matter, world, epoch)
    return consumers, producers, matter


# -- the conversions themselves ------------------------------------------------

def test_conversions_are_identity_at_the_reference_timebase_and_under_legacy():
    for value in (0.2, 0.009, 0.1, 0.004):
        assert per_tick_amount(value, 12, ELAPSED) == value
        assert per_tick_fraction(value, 12, ELAPSED) == value
        assert per_tick_amount(value, 365, LEGACY) == value
        assert per_tick_fraction(value, 365, LEGACY) == value
    assert scaled_ticks(5, 12, ELAPSED) == 5 and scaled_ticks(5, 365, LEGACY) == 5
    assert scaled_ticks(5, 365, ELAPSED) == 152


def test_conversions_preserve_a_month_at_daily_ticks():
    days_per_month = 365 / 12
    assert per_tick_amount(0.2, 365, ELAPSED) * days_per_month == pytest.approx(0.2, rel=1e-12)
    remaining = (1.0 - per_tick_fraction(0.05, 365, ELAPSED)) ** days_per_month
    assert remaining == pytest.approx(0.95, rel=1e-12)


def test_unknown_timebase_is_rejected():
    with pytest.raises(ValueError):
        per_tick_amount(0.2, 365, "per-day")
    with pytest.raises(ValueError):
        GenesisConfig(consumer_timebase="per-day")


# -- one animal, one simulated year --------------------------------------------

def test_basal_energy_and_water_loss_per_year_match_across_timebases():
    """No food or water anywhere, so the year's change is basal cost and water loss alone."""
    traits = trait_for("grazer")
    monthly, _, _ = _run_year(12, ELAPSED)
    daily, _, _ = _run_year(365, ELAPSED)
    legacy, _, _ = _run_year(365, LEGACY)
    m, d = monthly["animals"][0], daily["animals"][0]
    assert 10.0 - m["energy"] == pytest.approx(12 * traits.basal_cost, rel=1e-9)
    assert m["energy"] == pytest.approx(d["energy"], rel=1e-7)
    assert m["body_water_kg"] == pytest.approx(d["body_water_kg"], rel=1e-6)
    # The legacy timebase charged a month's water and energy every day: its
    # 0.30 kg of water lasts about 34 days, so the same animal dies of
    # dehydration within the year (before 365 x 0.2 energy would starve it).
    assert not legacy["animals"]
    assert legacy["cumulative_deaths_by_cause"]["dehydration"] == 1


def _plants(kg: float):
    def setup(consumers, producers, matter):
        cell = next(c for c in producers["cells"] if (c["x"], c["y"]) == (0, 0))
        for s in cell["plant_elements_kg"]:
            cell["plant_elements_kg"][s] = kg * PLANT_ELEMENT_FRACTIONS[s]
        for c in matter["cells"]:
            c["surface_water_kg"] = 50.0  # drinking is not under test
    return setup


@pytest.mark.parametrize("plant_kg", [0.02, 10.0], ids=["fraction-limited", "cap-limited"])
def test_plant_removed_per_year_matches_across_timebases(plant_kg):
    """A small stock is bitten by fraction (compounded per tick); a large one by the cap (linear)."""
    removed = {}
    for name, tpy, tb in (("monthly", 12, ELAPSED), ("daily", 365, ELAPSED), ("legacy", 365, LEGACY)):
        _, producers, _ = _run_year(tpy, tb, _plants(plant_kg))
        cell = next(c for c in producers["cells"] if (c["x"], c["y"]) == (0, 0))
        removed[name] = plant_kg - _mass(cell["plant_elements_kg"])
    assert removed["daily"] == pytest.approx(removed["monthly"], rel=1e-5)
    if plant_kg < 1.0:
        # Legacy took a month's bite fraction every day and stripped the patch.
        assert removed["legacy"] == pytest.approx(plant_kg, rel=1e-6)
        assert removed["monthly"] < 0.8 * plant_kg
    else:
        assert removed["legacy"] == pytest.approx(365 / 12 * removed["monthly"], rel=1e-5)


def test_carcass_decay_per_year_matches_across_timebases():
    def setup(consumers, producers, matter):
        consumers["animals"] = []
        cell = consumers["carcass_cells"][0]
        for s in cell["elements_kg"]:
            cell["elements_kg"][s] = PLANT_ELEMENT_FRACTIONS[s]  # 1 kg of decayed tissue
        cell["water_kg"] = 1.0
    left = {}
    for name, tpy, tb in (("monthly", 12, ELAPSED), ("daily", 365, ELAPSED), ("legacy", 365, LEGACY)):
        consumers, _, _ = _run_year(tpy, tb, setup)
        cell = consumers["carcass_cells"][0]
        left[name] = (_mass(cell["elements_kg"]), cell["water_kg"])
    assert left["monthly"][0] == pytest.approx(0.95 ** 12, rel=1e-6)
    assert left["daily"][0] == pytest.approx(left["monthly"][0], rel=1e-6)
    assert left["daily"][1] == pytest.approx(left["monthly"][1], rel=1e-5)
    assert left["legacy"][0] < 1e-6  # 0.95 ** 365: a month's decay applied daily


def test_matter_is_conserved_under_the_elapsed_timebase():
    """Element and water balance of a whole consumer world at daily ticks."""
    sim = GenesisSimulation(GenesisConfig(
        master_seed="timebase-conservation", world_width=6, world_height=6, ticks_per_year=365,
        producer_ecology_enabled=True, consumer_ecology_enabled=True))
    assert sim.config.canonical()["consumer_timebase"] == ELAPSED
    from tests.genesis.test_g3_consumers import combined_element_errors, combined_water_error
    sim.run(365)
    assert sim.ledger.verify_chain()
    assert all(abs(v) < 5e-5 for v in combined_element_errors(sim).values())
    assert abs(combined_water_error(sim)) < 1e-6


def test_monthly_runs_and_legacy_fingerprints_are_unchanged():
    base = dict(master_seed="fp", producer_ecology_enabled=True, consumer_ecology_enabled=True)
    assert "consumer_timebase" not in GenesisConfig(ticks_per_year=12, **base).canonical()
    assert "consumer_timebase" not in GenesisConfig(ticks_per_year=365, consumer_timebase=LEGACY, **base).canonical()
    sim = GenesisSimulation(GenesisConfig(ticks_per_year=12, **base))
    assert "rate_timebase" not in sim.consumer_state()
    assert not math.isnan(sim.consumer_state()["ticks_per_year"])
