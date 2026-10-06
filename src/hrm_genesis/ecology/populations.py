from __future__ import annotations

from .traits import trait_for


def living_population(state: dict, species: str | None = None) -> int:
    animals = state["animals"]
    if species is None:
        return len(animals)
    return sum(1 for animal in animals if animal["species"] == species)


def population_counts(state: dict) -> dict[str, int]:
    counts: dict[str, int] = {}
    for animal in state["animals"]:
        species = str(animal["species"])
        counts[species] = counts.get(species, 0) + 1
    return dict(sorted(counts.items()))


def mean_energy(state: dict, species: str) -> float:
    values = [
        float(a["energy"])
        for a in state["animals"]
        if a["species"] == species
    ]
    return 0.0 if not values else sum(values) / len(values)


def validate_species(state: dict) -> None:
    for animal in state["animals"]:
        trait_for(str(animal["species"]))
