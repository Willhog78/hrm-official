from __future__ import annotations

from typing import Sequence

from .entities import MatterEntity
from .properties import ELEMENT_TABLE

_TOL = 1e-6


class ConservationError(RuntimeError):
    """Raised when a transformation would violate mass or energy conservation.

    This is a runtime invariant enforced inside the transformation itself, not
    only checked afterward by tests -- per HRM's own rule that no mechanism is
    accepted merely because it looks correct on paper.
    """


def split(entity: MatterEntity, ratios: Sequence[float]) -> tuple[MatterEntity, ...]:
    """Split one entity into len(ratios) parts.

    Composition is identical across all parts and equal to the source entity
    (M2.9: this is a property of physical mixing/cutting, not a name-based
    special case -- no element symbol is inspected here at all). Mass and
    energy are divided proportionally to `ratios`. The source entity carries
    no privileged "parent" identity among the outputs (M2.5): all outputs are
    plain MatterEntity instances of equal standing.
    """
    if not ratios:
        raise ValueError("split requires at least one ratio")
    if any(r < 0 for r in ratios):
        raise ValueError("split ratios must be non-negative")
    total_ratio = sum(ratios)
    if abs(total_ratio - 1.0) > 1e-9:
        raise ValueError(f"split ratios must sum to 1.0, got {total_ratio}")

    parts = tuple(
        MatterEntity(
            composition=dict(entity.composition),
            mass_kg=entity.mass_kg * r,
            internal_energy_j=entity.internal_energy_j * r,
        )
        for r in ratios
    )

    out_mass = sum(p.mass_kg for p in parts)
    out_energy = sum(p.internal_energy_j for p in parts)
    if abs(out_mass - entity.mass_kg) > _TOL * max(1.0, entity.mass_kg):
        raise ConservationError(f"split violated mass conservation: {entity.mass_kg} -> {out_mass}")
    if abs(out_energy - entity.internal_energy_j) > _TOL * max(1.0, entity.internal_energy_j):
        raise ConservationError(f"split violated energy conservation: {entity.internal_energy_j} -> {out_energy}")
    return parts


def merge(entities: Sequence[MatterEntity]) -> MatterEntity:
    """Merge/mix two or more entities into one mass- and energy-conserving entity.

    Composition of the result is the mass-weighted union of inputs (M2.6).
    Merge is commutative/associative to tolerance because it is implemented as
    a plain sum over the input sequence with no order-dependent branching; the
    only order sensitivity is ordinary floating-point summation rounding,
    which is within the declared tolerance.
    """
    if len(entities) < 2:
        raise ValueError("merge requires at least two entities")

    in_mass = sum(e.mass_kg for e in entities)
    in_energy = sum(e.internal_energy_j for e in entities)

    elements = sorted({sym for e in entities for sym in e.composition})
    if not elements:
        raise ValueError("cannot merge entities with no composition")

    if in_mass > 0:
        composition = {
            sym: sum(e.mass_kg * e.composition.get(sym, 0.0) for e in entities) / in_mass
            for sym in elements
        }
    else:
        # Zero-mass edge case (M2.10): no mass to weight by. Fall back to a
        # plain (unweighted) average across inputs so the result is still a
        # valid, deterministic composition rather than an undefined division.
        composition = {
            sym: sum(e.composition.get(sym, 0.0) for e in entities) / len(entities)
            for sym in elements
        }

    # Composition fractions can drift by float error; renormalize defensively
    # rather than trust the arithmetic above, then re-verify the drift was
    # actually small (a real invariant check, not a silent correction).
    total_fraction = sum(composition.values())
    if total_fraction <= 0:
        raise ConservationError("merge produced a non-physical zero-total composition")
    if abs(total_fraction - 1.0) > 1e-6:
        raise ConservationError(f"merge composition drifted outside tolerance: {total_fraction}")
    composition = {sym: frac / total_fraction for sym, frac in composition.items() if frac > 0}

    result = MatterEntity(composition=composition, mass_kg=in_mass, internal_energy_j=in_energy)

    if abs(result.mass_kg - in_mass) > _TOL * max(1.0, in_mass):
        raise ConservationError(f"merge violated mass conservation: {in_mass} -> {result.mass_kg}")
    if abs(result.internal_energy_j - in_energy) > _TOL * max(1.0, in_energy):
        raise ConservationError(f"merge violated energy conservation: {in_energy} -> {result.internal_energy_j}")
    return result


def add_energy(entity: MatterEntity, delta_j: float) -> MatterEntity:
    """Add (or, if negative, remove) thermal energy without changing mass or composition.

    This is the only way phase can change in Slice A: phase is a pure derived
    function of composition + internal_energy_j (M2.4), so crossing a
    threshold requires actually adding/removing energy through this function.
    """
    new_energy = entity.internal_energy_j + delta_j
    if new_energy < 0:
        raise ConservationError(f"cannot remove {abs(delta_j)}J from an entity holding only {entity.internal_energy_j}J")
    return MatterEntity(
        composition=dict(entity.composition),
        mass_kg=entity.mass_kg,
        internal_energy_j=new_energy,
    )
