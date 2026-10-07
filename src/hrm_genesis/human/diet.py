"""Agentus ingestion of locally present material (capacity model v1).

Four questions are kept separate:

1. Does the material exist?  -> a real producer or consumer pool in this cell.
2. Can it be reached?        -> `access_kg` limits per tick (hands, handling).
3. Can it be digested?       -> `FOOD_KINDS[kind]["digestibility"]`, 0 for wood.
4. What results?             -> assimilated energy and elements, hazards, costs.

Whether a kind is *worth eating* is not supplied here. Agentus hold learned
expectations per kind (see `interactions.py`); only plant tissue has a declared
innate prior.

All quantities are dry mass. Energy densities are declared abstractions for
broad food classes, not biochemical models:

- plant tissue: the existing G10.2 calibration value (profile
  `food_energy_kcal_per_kg` x `assimilation`), unchanged.
- seed: 3800 kcal/kg, digestibility 0.75. Small dispersed seeds limit the
  gathering rate by hand.
- fresh animal tissue: 4800 kcal/kg, digestibility 0.90. Tearing by hand is
  slow; an edge raises the access rate (cutting, see interactions).
- decayed animal tissue: no assimilable energy; ingestion causes harm
  (an illness proxy recorded as injury, the model's only generic harm state).
- woody tissue: indigestible to Agentus; costs handling effort, yields nothing.

Unassimilated ingested mass is excreted into producer detritus in the same
cell, the existing G5 convention.
"""

from __future__ import annotations

from hrm_genesis.ecology.plants import PLANT_ELEMENT_FRACTIONS


FOOD_KINDS: dict[str, dict[str, float | str | None]] = {
    "plant_tissue": {"pool": "plant_elements_kg", "owner": "producer", "kcal_per_kg": -1.0, "digestibility": -1.0, "hand_access_kg": None, "handling_kcal_per_kg": 0.0, "hazard_per_kg": 0.0},
    "seed": {"pool": "seed_elements_kg", "owner": "producer", "kcal_per_kg": 3800.0, "digestibility": 0.75, "hand_access_kg": 0.45, "handling_kcal_per_kg": 60.0, "hazard_per_kg": 0.0},
    "fresh_tissue": {"pool": "fresh_elements_kg", "owner": "carcass", "kcal_per_kg": 4800.0, "digestibility": 0.90, "hand_access_kg": 0.25, "handling_kcal_per_kg": 40.0, "hazard_per_kg": 0.0},
    "decayed_tissue": {"pool": "elements_kg", "owner": "carcass", "kcal_per_kg": 0.0, "digestibility": 0.0, "hand_access_kg": 0.25, "handling_kcal_per_kg": 20.0, "hazard_per_kg": 0.6},
    "woody_tissue": {"pool": "woody_elements_kg", "owner": "producer", "kcal_per_kg": 0.0, "digestibility": 0.0, "hand_access_kg": 0.10, "handling_kcal_per_kg": 120.0, "hazard_per_kg": 0.0},
}
FOOD_KIND_ORDER = tuple(FOOD_KINDS)
MAX_INGESTION_HAZARD_PER_TICK = 0.25
SAMPLE_FRACTION_OF_GUT = 0.04


def _mass(elements: dict[str, float]) -> float:
    return sum(float(v) for v in elements.values())


def kind_energy_per_kg(kind: str, profile: dict) -> float:
    """Assimilable kcal per kg dry for a kind (physical truth, not perceived)."""
    spec = FOOD_KINDS[kind]
    if kind == "plant_tissue":
        return float(profile["food_energy_kcal_per_kg"]) * float(profile["assimilation"])
    return float(spec["kcal_per_kg"]) * float(spec["digestibility"])


def kind_assimilation(kind: str, profile: dict) -> float:
    if kind == "plant_tissue":
        return float(profile["assimilation"])
    return float(FOOD_KINDS[kind]["digestibility"])


def innate_food_prior(profile: dict) -> dict[str, float]:
    """Declared innate assumption: plant tissue is recognized as food.

    Every other kind starts unknown (no entry) and must be learned through
    ingestion experience.
    """
    return {"plant_tissue": kind_energy_per_kg("plant_tissue", profile)}


def pool_for(kind: str, producer_cell: dict, carcass_cell: dict | None) -> dict[str, float] | None:
    spec = FOOD_KINDS[kind]
    if spec["owner"] == "producer":
        return producer_cell.get(str(spec["pool"]))
    if carcass_cell is None:
        return None
    if kind == "fresh_tissue" and "fresh_elements_kg" not in carcass_cell:
        return None
    return carcass_cell.get(str(spec["pool"]))


def available_kg(kind: str, producer_cell: dict, carcass_cell: dict | None) -> float:
    pool = pool_for(kind, producer_cell, carcass_cell)
    return 0.0 if pool is None else max(0.0, _mass(pool))


def ingest(
    human: dict,
    kind: str,
    request_kg: float,
    producer_cell: dict,
    carcass_cell: dict | None,
    profile: dict,
    access_bonus_kg: float = 0.0,
) -> dict:
    """Move real mass from a pool into the body. Returns an intake record."""
    spec = FOOD_KINDS[kind]
    pool = pool_for(kind, producer_cell, carcass_cell)
    record = {"kind": kind, "kg": 0.0, "kcal": 0.0, "hazard": 0.0, "handling_kcal": 0.0}
    if pool is None:
        return record
    available = _mass(pool)
    scale = max(0.10, float(profile.get("development_scale", 1.0)))
    # Plant tissue keeps the pre-G10.3 behavior: no handling limit beyond gut capacity.
    access = float("inf") if spec["hand_access_kg"] is None else float(spec["hand_access_kg"]) * scale + max(0.0, access_bonus_kg)
    take = min(max(0.0, request_kg), available, access)
    if take <= 0.0 or available <= 0.0:
        return record
    fraction = take / available
    assimilation = kind_assimilation(kind, profile)
    target_dry_mass = float(profile.get("target_dry_mass_kg", profile["seed_dry_mass_kg"]))
    detritus = producer_cell["detritus_elements_kg"]
    taken = 0.0
    for symbol in sorted(pool):
        amount = float(pool[symbol]) * fraction
        pool[symbol] = float(pool[symbol]) - amount
        frac = float(PLANT_ELEMENT_FRACTIONS.get(symbol, 0.0))
        deficit = max(0.0, target_dry_mass * frac - float(human["body_elements_kg"].get(symbol, 0.0)))
        keep = min(amount * assimilation, deficit)
        human["body_elements_kg"][symbol] = float(human["body_elements_kg"].get(symbol, 0.0)) + keep
        detritus[symbol] = float(detritus.get(symbol, 0.0)) + amount - keep
        taken += amount
    kcal = taken * kind_energy_per_kg(kind, profile)
    handling = taken * float(spec["handling_kcal_per_kg"]) * scale
    human["energy"] = min(
        float(profile.get("energy_capacity_kcal", float("inf"))),
        float(human["energy"]) + kcal,
    ) - handling
    hazard = min(MAX_INGESTION_HAZARD_PER_TICK, taken * float(spec["hazard_per_kg"]) / max(0.1, scale))
    if hazard > 0.0:
        human["injury"] = float(human.get("injury", 0.0)) + hazard
    record.update(kg=taken, kcal=kcal, hazard=hazard, handling_kcal=handling)
    return record


def forage_at_cell(
    human: dict,
    producer_cell: dict,
    carcass_cell: dict | None,
    profile: dict,
    food_values: dict[str, float],
    try_kinds: tuple[str, ...] = (),
    access_bonus: dict[str, float] | None = None,
) -> list[dict]:
    """Ingest locally present kinds in order of learned value, up to gut capacity.

    `food_values` are the agent's own learned expectations (assimilated kcal per
    kg, net of what it has experienced). Kinds with no entry are unknown and are
    eaten only as small samples listed in `try_kinds` (bounded exploration).
    """
    access_bonus = access_bonus or {}
    gut = float(profile["bite_cap_kg"])
    records: list[dict] = []
    for kind in try_kinds:
        if available_kg(kind, producer_cell, carcass_cell) <= 0.0:
            continue
        rec = ingest(human, kind, gut * SAMPLE_FRACTION_OF_GUT, producer_cell, carcass_cell, profile, access_bonus.get(kind, 0.0))
        rec["sample"] = True
        gut -= rec["kg"]
        records.append(rec)
    ranked = sorted(
        (kind for kind, value in food_values.items() if value > 0.0 and kind in FOOD_KINDS),
        key=lambda k: (-float(food_values[k]), FOOD_KIND_ORDER.index(k)),
    )
    for kind in ranked:
        if gut <= 1e-12:
            break
        rec = ingest(human, kind, gut, producer_cell, carcass_cell, profile, access_bonus.get(kind, 0.0))
        rec["sample"] = False
        gut -= rec["kg"]
        if rec["kg"] > 0.0:
            records.append(rec)
    return records
