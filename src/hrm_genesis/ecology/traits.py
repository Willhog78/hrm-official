from __future__ import annotations

from dataclasses import dataclass


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

    def __post_init__(self) -> None:
        if self.perception_radius < 1:
            raise ValueError("perception_radius must be >= 1")
        if not 0.0 < self.assimilation_efficiency <= 1.0:
            raise ValueError("assimilation_efficiency must be in (0,1]")
        if self.maturity_ticks < 1 or self.max_age_ticks <= self.maturity_ticks:
            raise ValueError("invalid age thresholds")
        if not 0.0 < self.offspring_mass_fraction < 1.0:
            raise ValueError("offspring_mass_fraction must be in (0,1)")


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
        max_age_ticks=260,
        offspring_mass_fraction=0.18,
        water_capacity_kg=0.30,
        water_loss_per_tick_kg=0.012,
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
    ),
}


def trait_for(species: str) -> ConsumerTraits:
    try:
        return SPECIES[species]
    except KeyError as exc:
        raise ValueError(f"unknown consumer species: {species}") from exc
