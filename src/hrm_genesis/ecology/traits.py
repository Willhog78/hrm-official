from __future__ import annotations

from dataclasses import dataclass


TRAIT_REFERENCE_TICKS_PER_YEAR = 12


def scaled_life_history_ticks(value: int, ticks_per_year: int) -> int:
    if ticks_per_year < 1:
        raise ValueError("ticks_per_year must be >= 1")
    return max(1, int(round(int(value) * ticks_per_year / TRAIT_REFERENCE_TICKS_PER_YEAR)))


# Consumer rate timebase. Trait rates (energy, water and food per tick, and
# decay fractions per tick) are stated per reference tick, i.e. per month.
# "elapsed-time-v1" converts them to the run's tick length, as durations
# already are; "per-tick-legacy" applies them unchanged at any timebase and
# reproduces earlier runs. At the reference timebase both are identical.
CONSUMER_TIMEBASE_ELAPSED = "elapsed-time-v1"
CONSUMER_TIMEBASE_LEGACY = "per-tick-legacy"
CONSUMER_TIMEBASES = (CONSUMER_TIMEBASE_ELAPSED, CONSUMER_TIMEBASE_LEGACY)


def _converts(ticks_per_year: int, timebase: str) -> bool:
    if timebase not in CONSUMER_TIMEBASES:
        raise ValueError(f"unknown consumer timebase: {timebase}")
    return timebase == CONSUMER_TIMEBASE_ELAPSED and int(ticks_per_year) != TRAIT_REFERENCE_TICKS_PER_YEAR


def per_tick_amount(per_reference_tick: float, ticks_per_year: int, timebase: str) -> float:
    """A flow stated per month (energy, water, food mass) as an amount per tick."""
    if not _converts(ticks_per_year, timebase):
        return per_reference_tick
    return per_reference_tick * TRAIT_REFERENCE_TICKS_PER_YEAR / int(ticks_per_year)


def per_tick_fraction(per_reference_tick: float, ticks_per_year: int, timebase: str) -> float:
    """A fraction removed per month, compounded to the fraction per tick, so
    that the fraction remaining after a month is the same at any timebase."""
    if not _converts(ticks_per_year, timebase):
        return per_reference_tick
    return 1.0 - (1.0 - per_reference_tick) ** (TRAIT_REFERENCE_TICKS_PER_YEAR / int(ticks_per_year))


def scaled_ticks(value: int, ticks_per_year: int, timebase: str) -> int:
    """A count of reference ticks (months) as a count of ticks, under the
    given timebase; the legacy timebase leaves it unchanged."""
    if not _converts(ticks_per_year, timebase):
        return int(value)
    return scaled_life_history_ticks(value, ticks_per_year)


@dataclass(frozen=True)
class ConsumerTraits:
    species: str
    perception_radius: int
    movement_cost: float
    basal_cost: float
    bite_fraction: float
    assimilation_efficiency: float
    reproduction_energy: float
    maturity_ticks: int
    max_age_ticks: int
    offspring_mass_fraction: float
    water_capacity_kg: float
    water_loss_per_tick_kg: float
    reproduction_cooldown_ticks: int
    adult_body_mass_kg: float
    trophic_role: str = "herbivore"

    def __post_init__(self) -> None:
        if self.perception_radius < 1:
            raise ValueError("perception_radius must be >= 1")
        if not 0.0 < self.assimilation_efficiency <= 1.0:
            raise ValueError("assimilation_efficiency must be in (0,1]")
        if self.maturity_ticks < 1 or self.max_age_ticks <= self.maturity_ticks:
            raise ValueError("invalid age thresholds")
        if not 0.0 < self.offspring_mass_fraction < 1.0:
            raise ValueError("offspring_mass_fraction must be in (0,1)")
        if self.adult_body_mass_kg <= 0.0:
            raise ValueError("adult_body_mass_kg must be positive")
        if self.trophic_role not in {"herbivore", "predator"}:
            raise ValueError("unsupported trophic_role")


SPECIES: dict[str, ConsumerTraits] = {
    "grazer": ConsumerTraits(
        species="grazer",
        perception_radius=1,
        movement_cost=0.18,
        basal_cost=0.20,
        bite_fraction=0.10,
        assimilation_efficiency=0.58,
        reproduction_energy=13.0,
        maturity_ticks=28,
        max_age_ticks=320,
        offspring_mass_fraction=0.18,
        water_capacity_kg=0.30,
        water_loss_per_tick_kg=0.009,
        reproduction_cooldown_ticks=30,
        adult_body_mass_kg=0.050,
    ),
    "browser": ConsumerTraits(
        species="browser",
        perception_radius=2,
        movement_cost=0.26,
        basal_cost=0.18,
        bite_fraction=0.075,
        assimilation_efficiency=0.66,
        reproduction_energy=15.0,
        maturity_ticks=34,
        max_age_ticks=310,
        offspring_mass_fraction=0.15,
        water_capacity_kg=0.34,
        water_loss_per_tick_kg=0.010,
        reproduction_cooldown_ticks=45,
        adult_body_mass_kg=0.060,
    ),
    "stalker": ConsumerTraits(
        species="stalker",
        perception_radius=3,
        movement_cost=0.34,
        basal_cost=0.30,
        bite_fraction=0.0,
        assimilation_efficiency=0.72,
        reproduction_energy=24.0,
        maturity_ticks=60,
        max_age_ticks=420,
        offspring_mass_fraction=0.12,
        water_capacity_kg=0.42,
        water_loss_per_tick_kg=0.012,
        reproduction_cooldown_ticks=90,
        adult_body_mass_kg=0.085,
        trophic_role="predator",
    ),
}


def trait_for(species: str) -> ConsumerTraits:
    try:
        return SPECIES[species]
    except KeyError as exc:
        raise ValueError(f"unknown consumer species: {species}") from exc
