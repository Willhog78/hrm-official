"""Plant rates follow elapsed time (producer timebase elapsed-time-v1).

Plant rates and ages are stated per day (the daily world is the reference).
Under "elapsed-time-v1" a simulated year decomposes, germinates, dies and grows
the same at 12 and at 365 ticks/year; it is the identity at 365 ticks/year.
"per-tick-legacy" applies the daily values per tick at any timebase. Each test
uses one cell in fixed conditions (a static world state).
"""

from __future__ import annotations

import pytest

from hrm_genesis import GenesisConfig
from hrm_genesis.ecology.plants import (
    BASE_GROWTH_FRACTION,
    PLANT_ELEMENT_FRACTIONS,
    PRODUCER_TIMEBASE_ELAPSED as ELAPSED,
    PRODUCER_TIMEBASE_LEGACY as LEGACY,
    build_producer_state,
    evolve_producers,
    plant_age_ticks,
    plant_fraction_per_tick,
    plant_growth_per_tick,
)


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def _setup(tpy: int, timebase: str, *, solar: float, temperature: float, soil_water: float):
    producers = build_producer_state(width=2, height=2, ticks_per_year=tpy, timebase=timebase)
    matter = {
        "water_output_kg": 0.0,
        "cells": [{"x": c["x"], "y": c["y"], "soil_water_kg": soil_water, "surface_water_kg": 0.0,
                   "elements_kg": {s: 1.0e6 for s in PLANT_ELEMENT_FRACTIONS}} for c in producers["cells"]],
    }
    world = {"ticks_per_year": tpy,
             "cells": [{"x": c["x"], "y": c["y"], "solar": solar, "temperature": temperature,
                        "precipitation": 0.0, "lightning": 0.0} for c in producers["cells"]]}
    return producers, matter, world


def _cell(producers):
    return next(c for c in producers["cells"] if (c["x"], c["y"]) == (0, 0))


def _year(tpy, timebase, setup, **env):
    producers, matter, world = _setup(tpy, timebase, **env)
    setup(_cell(producers))
    for epoch in range(tpy):
        producers, matter = evolve_producers(producers, matter, world, epoch)
    return _cell(producers), matter


def test_conversions_are_identity_at_the_daily_reference_and_under_legacy():
    for v in (0.035, 0.0165, 0.012, 0.004, 0.055):
        assert plant_fraction_per_tick(v, 365, ELAPSED) == v
        assert plant_growth_per_tick(v, 365, ELAPSED) == v
        assert plant_fraction_per_tick(v, 12, LEGACY) == v
    assert plant_age_ticks(360, 365, ELAPSED) == 360
    assert plant_age_ticks(360, 12, ELAPSED) == 12
    assert plant_age_ticks(360, 12, LEGACY) == 360
    with pytest.raises(ValueError):
        GenesisConfig(producer_timebase="per-week")


def test_detritus_decomposition_per_year_matches_across_timebases():
    def setup(cell):
        for s in PLANT_ELEMENT_FRACTIONS:
            cell["detritus_elements_kg"][s] = PLANT_ELEMENT_FRACTIONS[s]  # 1 kg
    dark = dict(solar=0.0, temperature=22.0, soil_water=0.0)  # nothing grows, nothing germinates
    monthly, _ = _year(12, ELAPSED, setup, **dark)
    daily, _ = _year(365, ELAPSED, setup, **dark)
    legacy, _ = _year(12, LEGACY, setup, **dark)
    assert _mass(daily["detritus_elements_kg"]) == pytest.approx(0.965 ** 365, rel=1e-3)
    assert _mass(monthly["detritus_elements_kg"]) == pytest.approx(_mass(daily["detritus_elements_kg"]), rel=1e-3)
    assert _mass(legacy["detritus_elements_kg"]) == pytest.approx(0.965 ** 12, rel=1e-6)


def _span(tpy, timebase, days, setup, **env):
    """Run `days` of simulated time at `tpy` (days must be a whole number of ticks)."""
    producers, matter, world = _setup(tpy, timebase, **env)
    setup(_cell(producers))
    ticks = days * tpy // 365
    assert ticks * 365 == days * tpy
    for epoch in range(ticks):
        producers, matter = evolve_producers(producers, matter, world, epoch)
    return _cell(producers)


def test_mortality_under_constant_stress_matches_across_timebases():
    """73 ticks/year is exactly 5 days per tick, so spans compare exactly."""
    def setup(cell):
        for s in PLANT_ELEMENT_FRACTIONS:
            cell["plant_elements_kg"][s] = 10.0 * PLANT_ELEMENT_FRACTIONS[s]
    # No water: growth and germination are zero; stress is 1, so daily
    # mortality is min(0.85, 0.004 + 0.08) = 0.084.
    dry = dict(solar=1.0, temperature=22.0, soil_water=0.0)
    five_day = _span(73, ELAPSED, 20, setup, **dry)
    daily = _span(365, ELAPSED, 20, setup, **dry)
    legacy = _span(73, LEGACY, 20, setup, **dry)
    assert _mass(daily["plant_elements_kg"]) == pytest.approx(10.0 * (1 - 0.084) ** 20, rel=1e-6)
    assert _mass(five_day["plant_elements_kg"]) == pytest.approx(_mass(daily["plant_elements_kg"]), rel=1e-6)
    assert _mass(legacy["plant_elements_kg"]) == pytest.approx(10.0 * (1 - 0.084) ** 4, rel=1e-6)


def test_growth_matches_across_timebases():
    """Ample water and nutrients, ideal light and temperature. Growth compounds at
    the daily rate; within a tick growth precedes mortality and seeding, so a
    coarse tick and five daily ticks differ only by that ordering."""
    def setup(cell):
        for s in PLANT_ELEMENT_FRACTIONS:
            cell["plant_elements_kg"][s] = 0.05 * PLANT_ELEMENT_FRACTIONS[s]
    lush = dict(solar=1.0, temperature=22.0, soil_water=1.0e9)
    live = lambda c: _mass(c["plant_elements_kg"]) + _mass(c["woody_elements_kg"]) + _mass(c["seed_elements_kg"])  # noqa: E731
    five_day = _span(73, ELAPSED, 10, setup, **lush)
    daily = _span(365, ELAPSED, 10, setup, **lush)
    legacy = _span(73, LEGACY, 10, setup, **lush)
    assert live(daily) > 0.05 * 1.5
    assert live(five_day) == pytest.approx(live(daily), rel=0.05)
    # Legacy applies one day's growth per 5-day tick.
    assert live(legacy) < 0.05 + 0.5 * (live(daily) - 0.05)


def test_matter_is_conserved_with_converted_plants():
    from hrm_genesis import GenesisSimulation
    from tests.genesis.test_g3_consumers import combined_element_errors, combined_water_error
    sim = GenesisSimulation(GenesisConfig(master_seed="plant-conservation", world_width=6, world_height=6,
                                          ticks_per_year=12, producer_ecology_enabled=True, consumer_ecology_enabled=True))
    assert sim.config.canonical()["producer_timebase"] == ELAPSED
    sim.run(12 * 10)
    assert sim.ledger.verify_chain()
    assert all(abs(v) < 5e-5 for v in combined_element_errors(sim).values())
    assert abs(combined_water_error(sim)) < 1e-6


def test_daily_and_legacy_fingerprints_are_unchanged():
    base = dict(master_seed="fp", producer_ecology_enabled=True)
    assert "producer_timebase" not in GenesisConfig(ticks_per_year=365, **base).canonical()
    assert "producer_timebase" not in GenesisConfig(ticks_per_year=12, producer_timebase=LEGACY, **base).canonical()
    assert "rate_timebase" not in build_producer_state(width=2, height=2)
