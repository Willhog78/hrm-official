from __future__ import annotations

from dataclasses import dataclass


class PropertyError(ValueError):
    pass


@dataclass(frozen=True)
class ElementProperties:
    """Numeric, name-agnostic physical properties for one element.

    Values are illustrative placeholders consistent with real-world ordering
    (e.g. iron's melting threshold sits far above water's) but are NOT claimed
    as empirically validated under HRM Master Plan v1.1 Section 8. They are
    Structural / Live-but-unvalidated pending Stage-2 empirical calibration.
    All units are internally consistent (kg, J, J/kg) rather than tied to a
    specific unit-conversion claim.

    specific_heat_j_per_kg_k: energy to raise 1kg by 1 unit of internal
        temperature-equivalent, per phase. Used only to keep the specific-energy
        thresholds below physically ordered relative to each other; HRM does not
        track a separate Kelvin temperature state in Stage-2 Slice A.
    melt_threshold_j_per_kg: specific internal energy at which this element
        transitions solid -> liquid.
    boil_threshold_j_per_kg: specific internal energy at which this element
        transitions liquid -> gas. Must exceed melt_threshold_j_per_kg.
    latent_fusion_j_per_kg: extra specific energy absorbed while crossing the
        melt threshold before phase state advances (models latent heat without
        tracking temperature separately).
    latent_vapor_j_per_kg: extra specific energy absorbed while crossing the
        boil threshold before phase state advances.
    """

    symbol: str
    molar_mass_kg_per_mol: float
    specific_heat_j_per_kg_k: float
    melt_threshold_j_per_kg: float
    boil_threshold_j_per_kg: float
    latent_fusion_j_per_kg: float
    latent_vapor_j_per_kg: float

    def __post_init__(self):
        if self.molar_mass_kg_per_mol <= 0:
            raise PropertyError(f"{self.symbol}: molar mass must be positive")
        if self.specific_heat_j_per_kg_k <= 0:
            raise PropertyError(f"{self.symbol}: specific heat must be positive")
        if self.melt_threshold_j_per_kg < 0:
            raise PropertyError(f"{self.symbol}: melt threshold must be >= 0")
        if self.boil_threshold_j_per_kg <= self.melt_threshold_j_per_kg:
            raise PropertyError(f"{self.symbol}: boil threshold must exceed melt threshold")
        if self.latent_fusion_j_per_kg < 0 or self.latent_vapor_j_per_kg < 0:
            raise PropertyError(f"{self.symbol}: latent heats must be >= 0")


# Illustrative placeholder table. Ordering across elements is physically sane
# (iron's thresholds >> water's, hydrogen's thresholds are lowest) but absolute
# values are not calibrated against real thermodynamic data. Structural / Live
# but unvalidated (Section 8) until a dedicated empirical-calibration pass.
ELEMENT_TABLE: dict[str, ElementProperties] = {
    "H": ElementProperties("H", 0.001008, 14300.0, 14.0, 20.0, 58.0, 452.0),
    "O": ElementProperties("O", 0.016000, 918.0, 54.0, 90.0, 14.0, 214.0),
    "C": ElementProperties("C", 0.012011, 710.0, 3915.0, 4300.0, 105.0, 355.0),
    "Fe": ElementProperties("Fe", 0.055845, 449.0, 1811.0, 3134.0, 247.0, 6090.0),
    "Au": ElementProperties("Au", 0.196967, 129.0, 1337.0, 3129.0, 63.7, 1645.0),
    "Si": ElementProperties("Si", 0.028085, 705.0, 1687.0, 3538.0, 1787.0, 12800.0),
}


def require_known(symbol: str) -> ElementProperties:
    props = ELEMENT_TABLE.get(symbol)
    if props is None:
        raise PropertyError(f"unknown element symbol: {symbol!r}")
    return props
