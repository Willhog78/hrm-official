"""Discrete material objects: stone fragments, fibers, wood pieces, assemblies.

This module is material physics only. It knows masses, geometry, hardness,
toughness, friction and tension. It does not know organisms, intentions,
techniques or named products. Callers supply an applied work/force budget.

Simplifications (declared, not validated physics):

- A stone fragment's fixed properties come from its lithology table entry; only
  mass, edge sharpness and elongation are per-fragment state.
- Fracture is a threshold rule: delivered impact energy versus a size-scaled
  fracture energy. A fracture yields exactly two pieces whose masses sum to the
  parent's mass. New-edge sharpness depends on lithology and a deterministic
  geometry draw; it is never automatic.
- Fibers are one-dimensional strands with tensile strength proportional to
  cross-section, a friction coefficient and a moisture sensitivity.
- Binding uses a capstan-style friction hold: holding force grows with wrap
  angle and applied tension, is capped by binder strength, and is reduced by
  wetting for moisture-sensitive binders. Loads above the hold slip; loads
  above binder strength break the binder.
- Organic objects carry tracked elements; stone carries lithic mass only.
"""

from __future__ import annotations

import hashlib
import math


# ---------------------------------------------------------------------------
# Deterministic draws


def unit_draw(*parts: object) -> float:
    raw = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(raw[:8], "big") / float(2**64 - 1)


# ---------------------------------------------------------------------------
# Stone

# hardness: Mohs-like scale. fracture_j_per_kg23: energy (J) needed to fracture
# a 1 kg fragment; scales with mass^(2/3) (surface-area size effect).
# edge_potential: upper bound on new-edge sharpness from a fracture.
LITHOLOGIES: dict[str, dict[str, float]] = {
    "siliceous_fine": {"density": 2600.0, "hardness": 7.0, "fracture_j_per_kg23": 20.0, "edge_potential": 0.90, "roughness": 0.15},
    "basaltic": {"density": 2900.0, "hardness": 6.0, "fracture_j_per_kg23": 45.0, "edge_potential": 0.45, "roughness": 0.35},
    "granitic_coarse": {"density": 2700.0, "hardness": 6.0, "fracture_j_per_kg23": 70.0, "edge_potential": 0.15, "roughness": 0.70},
    "calcareous_soft": {"density": 2500.0, "hardness": 3.0, "fracture_j_per_kg23": 14.0, "edge_potential": 0.25, "roughness": 0.50},
}

MIN_FRAGMENT_KG = 0.005
NATURAL_FRAGMENT_MIN_KG = 0.08
NATURAL_FRAGMENT_MAX_KG = 4.0
MAX_NATURAL_FRAGMENTS_PER_CELL = 4


def cell_lithology(master_seed: str, x: int, y: int, elevation: float) -> str:
    """Bedrock type for a cell. Higher ground skews toward harder rock."""
    u = unit_draw(master_seed, "lithology", x, y)
    shift = max(0.0, min(0.25, (float(elevation) - 400.0) / 2400.0))
    u = min(0.999999, u + shift)
    names = sorted(LITHOLOGIES)  # basaltic, calcareous_soft, granitic_coarse, siliceous_fine
    return names[int(u * len(names))]


def seed_natural_fragments(world_cells: list[dict], master_seed: str) -> tuple[dict, float]:
    """Loose weathered fragments where bedrock is exposed.

    Fixed bedrock (World `rock_exposure`) is not an extractable inventory in
    this model. Only these loose fragments are movable, and their total mass is
    the lithic ledger's fixed initial quantity.
    """
    cells: dict[str, list[dict]] = {}
    total = 0.0
    for wc in sorted(world_cells, key=lambda c: (int(c["y"]), int(c["x"]))):
        x, y = int(wc["x"]), int(wc["y"])
        exposure = float(wc.get("rock_exposure", 0.0))
        count = int(exposure * (MAX_NATURAL_FRAGMENTS_PER_CELL + 1) * unit_draw(master_seed, "talus", x, y))
        count = min(MAX_NATURAL_FRAGMENTS_PER_CELL, count)
        if count <= 0:
            continue
        lith = cell_lithology(master_seed, x, y, float(wc.get("elevation", 0.0)))
        fragments = []
        for i in range(count):
            u = unit_draw(master_seed, "fragment-mass", x, y, i)
            mass = NATURAL_FRAGMENT_MIN_KG * (NATURAL_FRAGMENT_MAX_KG / NATURAL_FRAGMENT_MIN_KG) ** u
            mass = round(mass, 10)
            # Weathered fragments are mostly rounded; edges are dull.
            sharp = round(0.05 + 0.15 * unit_draw(master_seed, "fragment-edge", x, y, i), 10)
            elong = round(1.0 + 1.5 * unit_draw(master_seed, "fragment-shape", x, y, i), 10)
            fragments.append({"id": f"stone-{x}-{y}-{i}", "lith": lith, "m": mass, "s": sharp, "e": elong})
            total += mass
        cells[f"{x},{y}"] = fragments
    return cells, round(total, 10)


def stone_props(fragment: dict) -> dict[str, float]:
    lith = LITHOLOGIES[str(fragment["lith"])]
    mass = max(MIN_FRAGMENT_KG, float(fragment["m"]))
    volume = mass / lith["density"]
    size_m = (volume * float(fragment.get("e", 1.0))) ** (1.0 / 3.0)
    return {
        "mass_kg": float(fragment["m"]),
        "size_m": size_m,
        "hardness": lith["hardness"],
        "fracture_energy_j": lith["fracture_j_per_kg23"] * mass ** (2.0 / 3.0),
        "edge_sharpness": float(fragment.get("s", 0.0)),
        "roughness": lith["roughness"],
        # Moderate heating makes fine-grained siliceous rock fracture more
        # cleanly (declared simplification of heat treatment).
        "edge_potential": min(1.0, lith["edge_potential"] * (1.15 if fragment.get("ht") else 1.0)),
        "elongation": float(fragment.get("e", 1.0)),
    }


def fracture(fragment: dict, delivered_j: float, draw: float, draw2: float, new_id: str) -> tuple[dict, dict] | None:
    """Split a fragment if delivered energy exceeds its fracture energy.

    Returns (core, flake) with masses summing exactly to the parent, or None.
    """
    props = stone_props(fragment)
    if delivered_j < props["fracture_energy_j"] or float(fragment["m"]) < 2.0 * MIN_FRAGMENT_KG:
        return None
    parent = float(fragment["m"])
    split = 0.08 + 0.42 * draw  # flake fraction of parent mass
    flake_mass = round(max(MIN_FRAGMENT_KG, parent * split), 10)
    core_mass = round(parent - flake_mass, 10)
    # Thin flakes from fine-grained rock may carry sharp edges; geometry draw
    # decides. Coarse rock rarely does. Excess energy tends to crush the edge.
    crush = max(0.0, min(0.5, (delivered_j / props["fracture_energy_j"] - 3.0) * 0.1))
    flake_sharp = props["edge_potential"] * (0.25 + 0.75 * draw2) * (1.0 - split) * (1.0 - crush)
    core_sharp = max(float(fragment.get("s", 0.0)), props["edge_potential"] * 0.35 * draw2 * (1.0 - crush))
    core = dict(fragment, m=core_mass, s=round(min(1.0, core_sharp), 10))
    flake = {
        "id": new_id,
        "lith": fragment["lith"],
        "m": flake_mass,
        "s": round(min(1.0, flake_sharp), 10),
        "e": round(1.0 + 2.5 * (1.0 - split), 10),
    }
    return core, flake


def heat_stone(fragment: dict, intensity: float, draw: float, new_id: str) -> tuple[dict, dict | None]:
    """Fire acting on a stone. Strong heat can crack it (thermal shock, mass
    conserved); moderate heat on fine siliceous rock marks it heat-treated."""
    if intensity >= 0.6 and draw < 0.15:
        props = stone_props(fragment)
        pieces = fracture(fragment, props["fracture_energy_j"] * 1.01, draw * 6.0, 0.2, new_id)
        if pieces is not None:
            core, flake = pieces
            # Thermal cracking does not produce worked edges.
            core["s"] = fragment.get("s", 0.0)
            flake["s"] = round(min(float(flake["s"]), 0.15), 10)
            return core, flake
    if 0.2 <= intensity < 0.6 and fragment["lith"] == "siliceous_fine":
        fragment = dict(fragment, ht=True)
    return fragment, None


def edge_wear(fragment: dict, target_hardness: float) -> None:
    """Using an edge dulls it; harder targets dull it faster."""
    lith = LITHOLOGIES[str(fragment["lith"])]
    rate = 0.01 + 0.04 * min(2.0, target_hardness / max(0.5, lith["hardness"]))
    fragment["s"] = round(max(0.0, float(fragment.get("s", 0.0)) - rate), 10)


# ---------------------------------------------------------------------------
# Fibers and organic pieces

# strength_mpa: tensile strength of the dry strand material.
# moisture: fractional strength/friction change when wet (negative = weakens).
FIBER_SOURCES: dict[str, dict[str, float]] = {
    "plant": {"length_m": (0.15, 0.7), "thickness_mm": (0.6, 1.5), "flexibility": 0.85, "strength_mpa": 60.0, "friction": 0.45, "moisture": 0.10},
    "bark": {"length_m": (0.3, 1.4), "thickness_mm": (1.0, 3.0), "flexibility": 0.55, "strength_mpa": 45.0, "friction": 0.60, "moisture": -0.25},
    "tendon": {"length_m": (0.05, 0.25), "thickness_mm": (0.8, 2.0), "flexibility": 0.75, "strength_mpa": 90.0, "friction": 0.35, "moisture": -0.60},
}
FIBER_DENSITY = 1300.0  # kg/m^3, dry


def _span(bounds: tuple[float, float], u: float) -> float:
    return bounds[0] + (bounds[1] - bounds[0]) * u


def make_fiber(source: str, elements_kg: dict[str, float], u1: float, u2: float, object_id: str, length_scale: float = 1.0) -> dict:
    spec = FIBER_SOURCES[source]
    length = _span(spec["length_m"], u1) * max(0.05, min(1.0, length_scale))
    thickness = _span(spec["thickness_mm"], u2)
    return {
        "id": object_id,
        "material": "fiber",
        "source": source,
        "elements_kg": dict(elements_kg),
        "length_m": round(length, 10),
        "thickness_mm": round(thickness, 10),
        "flexibility": spec["flexibility"],
        "friction": spec["friction"],
        "moisture_sensitivity": spec["moisture"],
        "strands": 1,
        "integrity": 1.0,
    }


def fiber_mass_for(source: str, length_m: float, thickness_mm: float) -> float:
    radius = thickness_mm / 2000.0
    return math.pi * radius * radius * length_m * FIBER_DENSITY


def tensile_strength_n(fiber: dict, wetness: float = 0.0) -> float:
    spec = FIBER_SOURCES[str(fiber["source"])]
    radius = float(fiber["thickness_mm"]) / 2000.0
    area = math.pi * radius * radius
    base = spec["strength_mpa"] * 1e6 * area * float(fiber.get("integrity", 1.0))
    wet = 1.0 + float(fiber["moisture_sensitivity"]) * max(0.0, min(1.0, wetness))
    return base * max(0.1, wet)


def make_wood_piece(elements_kg: dict[str, float], u1: float, u2: float, object_id: str, max_length_m: float) -> dict:
    mass = sum(float(v) for v in elements_kg.values())
    length = min(max_length_m, 0.3 + 1.2 * u1)
    # Dry wood ~600 kg/m^3; diameter follows from mass and length.
    diameter = math.sqrt(max(1e-9, mass / (600.0 * length)) * 4.0 / math.pi)
    return {
        "id": object_id,
        "material": "wood",
        "elements_kg": dict(elements_kg),
        "length_m": round(length, 10),
        "diameter_m": round(diameter, 10),
        "stiffness": round(0.5 + 0.5 * u2, 10),
    }


def object_mass(obj: dict) -> float:
    if obj["material"] == "stone":
        return float(obj["fragment"]["m"])
    if obj["material"] == "assembly":
        return sum(object_mass(c) for c in obj["components"]) + object_mass(obj["binder"])
    if obj["material"] == "surface":
        return sum(object_mass(strand) for strand in obj["strands"])
    return sum(float(v) for v in obj.get("elements_kg", {}).values())


def object_elements(obj: dict) -> dict[str, float]:
    if obj["material"] == "stone":
        return {}
    if obj["material"] == "assembly":
        total: dict[str, float] = {}
        for part in list(obj["components"]) + [obj["binder"]]:
            for s, v in object_elements(part).items():
                total[s] = total.get(s, 0.0) + float(v)
        return total
    if obj["material"] == "surface":
        total = {}
        for part in obj["strands"]:
            for s, v in object_elements(part).items():
                total[s] = total.get(s, 0.0) + float(v)
        return total
    return {s: float(v) for s, v in obj.get("elements_kg", {}).items()}


def object_lithic_mass(obj: dict) -> float:
    if obj["material"] == "stone":
        return float(obj["fragment"]["m"])
    if obj["material"] == "assembly":
        return sum(object_lithic_mass(c) for c in obj["components"])
    return 0.0


def characteristic_size_m(obj: dict) -> float:
    if obj["material"] == "stone":
        return stone_props(obj["fragment"])["size_m"]
    if obj["material"] == "wood":
        return float(obj["diameter_m"])
    if obj["material"] == "assembly":
        return max(characteristic_size_m(c) for c in obj["components"])
    return 0.01


def split_elements(elements: dict[str, float], fraction: float) -> tuple[dict[str, float], dict[str, float]]:
    """Split element mass exactly: second = original - first."""
    first = {s: round(float(v) * fraction, 12) for s, v in elements.items()}
    second = {s: float(v) - first[s] for s, v in elements.items()}
    return first, second


def merge_elements(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    out = {s: float(v) for s, v in a.items()}
    for s, v in b.items():
        out[s] = out.get(s, 0.0) + float(v)
    return out


# ---------------------------------------------------------------------------
# Fiber manipulations


def twist(fibers: list[dict], object_id: str) -> dict:
    """Twist strands together. Friction lets strands share load; the twist
    shortens the result. No new material appears."""
    friction = min(float(f["friction"]) for f in fibers)
    efficiency = 0.55 + 0.35 * min(1.0, friction / 0.6)
    elements: dict[str, float] = {}
    for f in fibers:
        elements = merge_elements(elements, f["elements_kg"])
    length = min(float(f["length_m"]) for f in fibers) * 0.9
    thickness = math.sqrt(sum(float(f["thickness_mm"]) ** 2 for f in fibers))
    # Strength of the twisted strand relative to a single strand of the same
    # total section: carried by `integrity` so tensile_strength_n stays general.
    sources = sorted({str(f["source"]) for f in fibers})
    base = fibers[0]
    return {
        "id": object_id,
        "material": "fiber",
        "source": base["source"] if len(sources) == 1 else min(sources, key=lambda s: FIBER_SOURCES[s]["strength_mpa"]),
        "elements_kg": elements,
        "length_m": round(length, 10),
        "thickness_mm": round(thickness, 10),
        "flexibility": round(min(float(f["flexibility"]) for f in fibers) * 0.95, 10),
        "friction": round(friction, 10),
        "moisture_sensitivity": round(max((float(f["moisture_sensitivity"]) for f in fibers), key=abs), 10),
        "strands": int(sum(int(f.get("strands", 1)) for f in fibers)),
        "integrity": round(min(1.0, efficiency * min(float(f.get("integrity", 1.0)) for f in fibers)), 10),
    }


def break_fiber(fiber: dict, draw: float, new_id: str) -> tuple[dict, dict]:
    """Separate a strand into two pieces; mass splits exactly."""
    fraction = 0.25 + 0.5 * draw
    first_el, second_el = split_elements(fiber["elements_kg"], fraction)
    first = dict(fiber, elements_kg=first_el, length_m=round(float(fiber["length_m"]) * fraction, 10))
    second = dict(fiber, id=new_id, elements_kg=second_el, length_m=round(float(fiber["length_m"]) * (1.0 - fraction), 10))
    return first, second


def interlace(strands: list[dict], object_id: str) -> dict | None:
    """Cross strands into a surface. Coverage follows strand length and spacing;
    low-friction strands do not hold the pattern."""
    if len(strands) < 4:
        return None
    warp = strands[0::2]
    weft = strands[1::2]
    spacing = lambda group: sum(float(s["thickness_mm"]) for s in group) / len(group) / 1000.0 * 4.0
    width = min(min(float(s["length_m"]) for s in weft), len(warp) * spacing(warp))
    height = min(min(float(s["length_m"]) for s in warp), len(weft) * spacing(weft))
    friction = sum(float(s["friction"]) for s in strands) / len(strands)
    return {
        "id": object_id,
        "material": "surface",
        "strands": [dict(s) for s in strands],
        "area_m2": round(max(0.0, width * height), 10),
        "cohesion": round(min(1.0, friction / 0.5), 10),
    }


def wrap_and_tighten(binder: dict, parts: list[dict], applied_tension_n: float, wetness: float) -> dict:
    """Wrap a strand around parts and tighten it.

    Returns {"outcome": "bound"|"short"|"too_stiff"|"broke", ...}. A strand that
    is tightened beyond its strength breaks. A strand too short to make one turn
    around the parts cannot bind them.
    """
    girth = math.pi * sum(characteristic_size_m(p) for p in parts)
    length = float(binder["length_m"])
    if girth <= 0.0 or length < girth * 1.2:
        return {"outcome": "short"}
    smallest_radius = max(0.002, min(characteristic_size_m(p) for p in parts) / 2.0)
    # Stiff, thick strands crack when bent around small radii.
    bend_strain = (float(binder["thickness_mm"]) / 1000.0) / (2.0 * smallest_radius)
    if bend_strain * (1.0 - float(binder["flexibility"])) > 0.12:
        return {"outcome": "too_stiff"}
    strength = tensile_strength_n(binder, wetness)
    if applied_tension_n > strength:
        return {"outcome": "broke", "strength_n": strength}
    wraps = min(8.0, length / girth)
    friction = float(binder["friction"]) * (1.0 + float(binder["moisture_sensitivity"]) * max(0.0, min(1.0, wetness)) * 0.5)
    hold = applied_tension_n * (math.exp(max(0.05, friction) * 2.0 * math.pi * wraps) - 1.0)
    hold = min(hold, 2.0 * strength)
    return {"outcome": "bound", "hold_n": hold, "wraps": wraps, "strength_n": strength, "tension_n": applied_tension_n}


def binding_load_result(assembly: dict, load_n: float, wetness: float) -> str:
    """'holds', 'slips' (parts come apart, binder intact), or 'breaks'."""
    binder = assembly["binder"]
    strength = tensile_strength_n(binder, wetness)
    dry_strength = max(1e-9, tensile_strength_n(binder, 0.0))
    hold = float(assembly["hold_n"]) * (strength / dry_strength)
    if load_n > 2.0 * strength:
        return "breaks"
    if load_n > hold:
        return "slips"
    return "holds"


# ---------------------------------------------------------------------------
# Impact and cutting


def impact_energy_j(head_mass_kg: float, work_budget_j: float, hand_speed_m_s: float, lever_m: float = 0.0) -> float:
    """Energy delivered by swinging a head.

    Light heads are limited by achievable speed; heavy heads by the body's work
    budget. A rigid lever raises head speed for the same arm motion and lets
    the body put more of its work into the swing.
    """
    leverage = 1.0 + max(0.0, lever_m) / 0.7
    speed_limited = 0.5 * head_mass_kg * (hand_speed_m_s * leverage) ** 2
    work_limited = work_budget_j * math.sqrt(leverage)
    return max(0.0, min(speed_limited, work_limited))


def cutting_capacity(edge_sharpness: float, edge_hardness: float, target_hardness: float, force_scale: float) -> float:
    """0..1 measure of how readily an edge separates a target per stroke."""
    if edge_sharpness <= 0.0:
        return 0.0
    hardness_ratio = min(1.0, edge_hardness / max(0.1, target_hardness * 1.5))
    return max(0.0, min(1.0, edge_sharpness * hardness_ratio * max(0.0, min(1.0, force_scale))))
