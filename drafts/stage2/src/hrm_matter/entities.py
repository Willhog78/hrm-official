from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
import hashlib
import json

from .properties import require_known

_TOLERANCE = 1e-9


class Phase(Enum):
    SOLID = "SOLID"
    LIQUID = "LIQUID"
    GAS = "GAS"


class CompositionError(ValueError):
    pass


def _validate_composition(composition: dict[str, float]) -> dict[str, float]:
    if not composition:
        raise CompositionError("composition must contain at least one element")
    total = 0.0
    cleaned: dict[str, float] = {}
    for symbol, fraction in composition.items():
        require_known(symbol)  # raises PropertyError (a ValueError) if unknown
        if fraction < 0:
            raise CompositionError(f"negative mass fraction for {symbol}")
        if fraction > 0:
            cleaned[symbol] = float(fraction)
        total += fraction
    if abs(total - 1.0) > 1e-6:
        raise CompositionError(f"composition mass fractions must sum to 1.0, got {total}")
    return dict(sorted(cleaned.items()))


@dataclass(frozen=True)
class MatterEntity:
    """A discrete parcel of matter: composition, total mass, and total internal energy.

    Composition is real elemental mass-fraction data (M2.1), not an opaque
    registered ID: two entities with identical composition, mass and energy
    are physically interchangeable by construction (they are equal dataclass
    instances), and no transformation function ever branches on element name
    (M2.9) -- only on the numeric properties below.
    """

    composition: dict[str, float]  # element symbol -> mass fraction, sums to 1.0
    mass_kg: float
    internal_energy_j: float

    def __post_init__(self):
        # MatterEntity is a frozen dataclass, but `frozen=True` only blocks
        # reattaching the `composition` attribute itself -- it does not stop
        # ordinary code from mutating the dict object *inside* it in place
        # (`entity.composition["Fe"] = 999`), which would silently corrupt
        # kernel-owned state through nothing more exotic than a normal legal
        # read. Wrapping in MappingProxyType closes that: the mapping is
        # genuinely read-only, not just relabeled. (Found by attacking this
        # module's own `get()` path with ordinary code, no reflection.)
        validated = _validate_composition(self.composition)
        object.__setattr__(self, "composition", MappingProxyType(validated))
        if self.mass_kg < 0:
            raise CompositionError("mass_kg must be >= 0")
        if self.internal_energy_j < 0:
            raise CompositionError("internal_energy_j must be >= 0")

    @property
    def specific_energy_j_per_kg(self) -> float:
        if self.mass_kg == 0:
            return 0.0
        return self.internal_energy_j / self.mass_kg

    def _weighted(self, attr: str) -> float:
        return sum(
            fraction * getattr(require_known(symbol), attr)
            for symbol, fraction in self.composition.items()
        )

    @property
    def melt_complete_j_per_kg(self) -> float:
        return self._weighted("melt_threshold_j_per_kg") + self._weighted("latent_fusion_j_per_kg")

    @property
    def boil_complete_j_per_kg(self) -> float:
        return self._weighted("boil_threshold_j_per_kg") + self._weighted("latent_vapor_j_per_kg")

    @property
    def phase(self) -> Phase:
        # Derived only. There is no setter and no code path anywhere in this
        # package assigns Phase directly (M2.4): it is always recomputed from
        # composition + internal_energy_j.
        se = self.specific_energy_j_per_kg
        if se < self.melt_complete_j_per_kg:
            return Phase.SOLID
        if se < self.boil_complete_j_per_kg:
            return Phase.LIQUID
        return Phase.GAS

    def canonical(self) -> dict:
        # Convert the read-only composition view to a plain dict here: this
        # output is for hashing/serialization/checkpointing, where a plain
        # JSON-serializable dict is required, and returning a fresh dict here
        # cannot be used to mutate the entity's real internal state.
        return {
            "composition": dict(self.composition),
            "mass_kg": self.mass_kg,
            "internal_energy_j": self.internal_energy_j,
        }


def composition_digest(entity: MatterEntity) -> str:
    payload = json.dumps(entity.canonical(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
