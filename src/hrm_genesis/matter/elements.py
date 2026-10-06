from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Element:
    symbol: str
    atomic_number: int
    atomic_mass_u: float
    role: str


# Canonical Genesis element registry. This is intentionally broader than the
# set currently used by G1.5 so later biology/materials can activate elements
# without redefining identity. Only numeric/role metadata lives here; causal
# behavior belongs in processes, not element-name conditionals.
ELEMENTS: dict[str, Element] = {
    "H": Element("H", 1, 1.008, "water/organic"),
    "C": Element("C", 6, 12.011, "organic/carbon"),
    "N": Element("N", 7, 14.007, "biological nutrient"),
    "O": Element("O", 8, 15.999, "water/respiration"),
    "Na": Element("Na", 11, 22.990, "electrolyte/mineral"),
    "Mg": Element("Mg", 12, 24.305, "biological/mineral"),
    "Al": Element("Al", 13, 26.982, "mineral/material"),
    "Si": Element("Si", 14, 28.085, "mineral/material"),
    "P": Element("P", 15, 30.974, "biological nutrient"),
    "S": Element("S", 16, 32.06, "biological/mineral"),
    "Cl": Element("Cl", 17, 35.45, "electrolyte/mineral"),
    "K": Element("K", 19, 39.098, "biological nutrient"),
    "Ca": Element("Ca", 20, 40.078, "biological/mineral"),
    "Fe": Element("Fe", 26, 55.845, "biological/material"),
    "Cu": Element("Cu", 29, 63.546, "biological/material"),
    "Zn": Element("Zn", 30, 65.38, "biological/material"),
}


WATER_H_MASS_FRACTION = (2.0 * ELEMENTS["H"].atomic_mass_u) / (
    2.0 * ELEMENTS["H"].atomic_mass_u + ELEMENTS["O"].atomic_mass_u
)
WATER_O_MASS_FRACTION = 1.0 - WATER_H_MASS_FRACTION


def require_element(symbol: str) -> Element:
    try:
        return ELEMENTS[symbol]
    except KeyError as exc:
        raise ValueError(f"unknown element symbol: {symbol!r}") from exc
