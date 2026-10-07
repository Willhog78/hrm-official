"""Live Agentus interactions with local material and organisms (capacity model v1).

An Agentus may perform a few general interactions per tick with what is
physically present in its own cell: objects on the ground, objects in hand,
producer pools, carcass tissue and animals. Effects follow from material
properties (see `hrm_genesis.matter.objects`). Nothing here names a tool,
product or technique, and no sequence is preselected.

Choice uses the agent's own learned expectation per interaction key. A key is
`verb:target|held`, where target and held classes are perceivable physical
categories (an edge, a heavy stone, a stick, a strand), never value labels.
Untried interactions are sampled only through bounded, costed exploration.
Values learn from experienced bodily outcomes; a short eligibility trace
passes later food gains back to the interactions that preceded them.

Declared assumptions:
- Agentus perceive the mass, size, edge and texture of objects they see or
  hold, and the presence and kind of animals in their own and adjacent cells.
- Only plant tissue is innately recognized as food (see diet.py). Everything
  else is learned.
- Infants and dependent children do not perform interactions.
"""

from __future__ import annotations

import json
import math

from hrm_genesis.ecology.animals import displace_animal, kill_animal
from hrm_genesis.ecology.traits import trait_for
from hrm_genesis.matter import objects as mo

from .actions import execute_live_sequence
from .diet import FOOD_KINDS, available_kg, innate_food_prior


CAPACITY_MODEL = "capacity-v2"

MAX_INTERACTIONS_PER_TICK = 3
MAX_RIGID_IN_HAND = 2
MAX_SOFT_IN_HAND = 6
CARRY_LIMIT_KG = 20.0
WORK_PER_SWING_J = 120.0
HAND_SPEED_M_S = 9.0
MAX_PULL_TENSION_N = 250.0
VALUE_LEARNING_RATE = 0.3
FOOD_LEARNING_RATE = 0.4
TRACE_DECAY = 0.7
TRACE_LENGTH = 8
HISTORY_DECAY = 0.8
HISTORY_LENGTH = 16
OBSERVATION_RATE = 0.5
EXPLORE_HUNGRY = 0.25
EXPLORE_SATED = 0.08
RETRY_KNOWN = 0.03
FOOD_SAMPLE_HUNGRY = 0.5
FOOD_SAMPLE_SATED = 0.1
FATIGUE_PER_INTERACTION = 0.02
MIN_INTERACTION_KCAL = 2.0
INSULATION_MAX_C = 8.0
BODY_SURFACE_M2 = 1.8
ORGANIC_DECAY_GROUND = 0.005
ORGANIC_DECAY_HELD = 0.002

RIGID = {"stone", "wood", "assembly"}
SOFT = {"fiber", "surface"}


# ---------------------------------------------------------------------------
# Setup and accounting


def enable_capacities(human_state: dict) -> dict:
    state = dict(human_state)
    state["capacity_model"] = CAPACITY_MODEL
    state.setdefault("objects", [])
    state.setdefault("next_object_ordinal", 0)
    state.setdefault("capacity_stats", empty_stats())
    profile = state["physiology_profile"]
    people = []
    for person in state["humans"]:
        person = dict(person)
        if "cognition" in person:
            init_capacity_cognition(person, profile)
        people.append(person)
    state["humans"] = people
    return state


def init_capacity_cognition(person: dict, profile: dict) -> None:
    cognition = dict(person["cognition"])
    cognition.setdefault("food_values", innate_food_prior(profile))
    cognition.setdefault("affordance_values", {})
    cognition.setdefault("trace", [])
    person["cognition"] = cognition


def empty_stats() -> dict:
    return {
        "intake_kg_by_kind": {},
        "intake_kcal_by_kind": {},
        "ingestion_hazard": 0.0,
        "interaction_counts": {},
        "interaction_injury": 0.0,
        "interaction_effort_kcal": 0.0,
        "capture_attempts": 0,
        "captures": 0,
        "capture_escapes": 0,
        "fractures": 0,
        "sharp_flakes": 0,
        "bindings": 0,
        "binding_failures": 0,
        "binding_load_slips": 0,
        "binding_load_breaks": 0,
        "fibers_extracted": 0,
        "wood_pieces": 0,
        "surfaces": 0,
        "worn_surfaces": 0,
    }


def _bump(stats: dict, key: str, amount: float = 1) -> None:
    stats[key] = stats.get(key, 0) + amount


def _bump_map(stats: dict, key: str, sub: str, amount: float) -> None:
    bucket = dict(stats.get(key, {}))
    bucket[sub] = bucket.get(sub, 0) + amount
    stats[key] = bucket


def lithic_inventory_kg(matter_state: dict, human_state: dict | None) -> float:
    total = 0.0
    for fragments in matter_state.get("lithic_cells", {}).values():
        total += sum(float(f["m"]) for f in fragments)
    if human_state is not None:
        total += sum(mo.object_lithic_mass(o) for o in human_state.get("objects", []))
    return total


def object_element_totals(human_state: dict) -> dict[str, float]:
    totals: dict[str, float] = {}
    for obj in human_state.get("objects", []):
        for symbol, amount in mo.object_elements(obj).items():
            totals[symbol] = totals.get(symbol, 0.0) + float(amount)
    return totals


# ---------------------------------------------------------------------------
# Object helpers


def _new_id(humans: dict, prefix: str) -> str:
    ordinal = int(humans.get("next_object_ordinal", 0))
    humans["next_object_ordinal"] = ordinal + 1
    return f"{prefix}-{ordinal:08d}"


def _place(obj: dict, x: int, y: int, holder: str | None) -> dict:
    obj["x"], obj["y"], obj["holder"] = int(x), int(y), holder
    obj.setdefault("worn", False)
    return obj


def held_objects(humans: dict, agent_id: str) -> list[dict]:
    return [o for o in humans["objects"] if o.get("holder") == agent_id and not o.get("worn")]


def ground_objects(humans: dict, xy: tuple[int, int]) -> list[dict]:
    return [o for o in humans["objects"] if o.get("holder") is None and (int(o["x"]), int(o["y"])) == xy]


def carry_objects(humans: dict, agent_id: str, xy: tuple[int, int]) -> None:
    for obj in humans["objects"]:
        if obj.get("holder") == agent_id:
            obj["x"], obj["y"] = int(xy[0]), int(xy[1])


def drop_all(humans: dict, agent_id: str) -> None:
    for obj in humans["objects"]:
        if obj.get("holder") == agent_id:
            obj["holder"] = None
            obj["worn"] = False


def insulation_c(humans: dict, agent_id: str) -> float:
    """Cold-exposure moderation from surfaces worn on the body."""
    coverage = 0.0
    for obj in humans.get("objects", []):
        if obj.get("holder") == agent_id and obj.get("worn") and obj["material"] == "surface":
            coverage += float(obj["area_m2"]) * float(obj["cohesion"])
    return INSULATION_MAX_C * min(1.0, coverage / BODY_SURFACE_M2)


def _stone_class(fragment: dict) -> str:
    if float(fragment.get("s", 0.0)) >= 0.4:
        return "stone_edged"
    if float(fragment["m"]) >= 0.5:
        return "stone_heavy"
    return "stone_small"


def object_class(obj: dict | None) -> str:
    if obj is None:
        return "none"
    material = obj["material"]
    if material == "stone":
        return _stone_class(obj["fragment"])
    if material == "wood":
        return "stick" if float(obj["length_m"]) >= 0.6 else "wood_short"
    if material == "fiber":
        return f"strand_{obj['source']}"
    if material == "surface":
        return "surface"
    if material == "assembly":
        heads = [c for c in obj["components"] if c["material"] == "stone"]
        handles = [c for c in obj["components"] if c["material"] == "wood"]
        if heads and handles:
            return f"bound_{_stone_class(heads[0]['fragment'])}_on_stick"
        return "bound_bundle"
    return material


def _head_and_lever(obj: dict) -> tuple[float, float, float, float, dict | None]:
    """Mass of the striking part, lever length, hardness, edge, and the stone
    fragment at the striking face (if any)."""
    material = obj["material"]
    if material == "stone":
        props = mo.stone_props(obj["fragment"])
        return props["mass_kg"], 0.0, props["hardness"], props["edge_sharpness"], obj["fragment"]
    if material == "wood":
        mass = mo.object_mass(obj)
        return mass * 0.5, float(obj["length_m"]) * 0.5, 2.0, 0.0, None
    if material == "assembly":
        heads = [c for c in obj["components"] if c["material"] == "stone"]
        handles = [c for c in obj["components"] if c["material"] == "wood"]
        if heads:
            head = max(heads, key=lambda c: float(c["fragment"]["m"]))
            props = mo.stone_props(head["fragment"])
            lever = max((float(h["length_m"]) for h in handles), default=0.0)
            return props["mass_kg"], lever, props["hardness"], props["edge_sharpness"], head["fragment"]
        mass = mo.object_mass(obj)
        return mass * 0.5, 0.0, 2.0, 0.0, None
    return mo.object_mass(obj), 0.0, 1.0, 0.0, None


def _reach_m(obj: dict | None) -> float:
    if obj is None:
        return 0.0
    if obj["material"] == "wood":
        return float(obj["length_m"])
    if obj["material"] == "assembly":
        return max((float(c.get("length_m", 0.0)) for c in obj["components"]), default=0.0)
    return 0.0


def _capability(human: dict, profile: dict) -> float:
    scale = float(profile.get("development_scale", 1.0))
    fatigue = float(human.get("fatigue", 0.0))
    injury = min(1.0, float(human.get("injury", 0.0)))
    return max(0.0, scale * (1.0 - 0.5 * fatigue) * (1.0 - 0.6 * injury))


def _debit_pool(pool: dict[str, float], mass: float) -> dict[str, float]:
    total = sum(float(v) for v in pool.values())
    if total <= 0.0 or mass <= 0.0:
        return {s: 0.0 for s in pool}
    fraction = min(1.0, mass / total)
    taken = {}
    for symbol in sorted(pool):
        amount = float(pool[symbol]) * fraction
        pool[symbol] = float(pool[symbol]) - amount
        taken[symbol] = amount
    return taken


# ---------------------------------------------------------------------------
# Context and affordances


class Context:
    def __init__(self, humans, human, profile, pcell, ccell, lithic_cells, wcell, consumers, epoch):
        self.humans = humans
        self.human = human
        self.profile = profile
        self.pcell = pcell
        self.ccell = ccell
        self.lithic_cells = lithic_cells
        self.wcell = wcell
        self.consumers = consumers
        self.epoch = epoch
        self.xy = (int(human["x"]), int(human["y"]))
        self.access_bonus: dict[str, float] = {}
        self.produced: dict[str, float] = {}
        self.stats = humans.setdefault("capacity_stats", empty_stats())
        self.performed: list[tuple[str, dict]] = []

    @property
    def agent_id(self) -> str:
        return str(self.human["id"])

    def wetness(self) -> float:
        return max(0.0, min(1.0, float(self.wcell.get("precipitation", 0.0)) / 3.0))

    def draw(self, *parts: object) -> float:
        return mo.unit_draw(self.agent_id, self.epoch, *parts)

    def held(self) -> list[dict]:
        return held_objects(self.humans, self.agent_id)

    def rigid_held(self) -> list[dict]:
        return [o for o in self.held() if o["material"] in RIGID]

    def soft_held(self) -> list[dict]:
        return [o for o in self.held() if o["material"] in SOFT]

    def held_mass(self) -> float:
        return sum(mo.object_mass(o) for o in self.held()) + sum(
            float(v) for v in self.human.get("held_material_elements_kg", {}).values()
        )

    def mcell_lithics(self) -> list[dict]:
        """Natural loose fragments in this cell (Matter-owned inventory)."""
        return self.lithic_cells.get(f"{self.xy[0]},{self.xy[1]}", [])

    def animals_here(self) -> list[dict]:
        return [
            a for a in self.consumers.get("animals", [])
            if (int(a["x"]), int(a["y"])) == self.xy
        ]


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def enumerate_affordances(ctx: Context) -> list[tuple[str, dict]]:
    """Every interaction physically possible here, keyed by perceivable classes."""
    options: list[tuple[str, dict]] = []
    rigid = ctx.rigid_held()
    soft = ctx.soft_held()
    hands_free_rigid = len(rigid) < MAX_RIGID_IN_HAND
    hands_free_soft = len(soft) < MAX_SOFT_IN_HAND
    carry_room = CARRY_LIMIT_KG * max(0.1, float(ctx.profile.get("development_scale", 1.0))) - ctx.held_mass()

    # Grasp loose things on the ground.
    seen = set()
    for frag in ctx.mcell_lithics():
        if hands_free_rigid and float(frag["m"]) <= carry_room:
            key = f"grasp:{_stone_class(frag)}|none"
            if key not in seen:
                seen.add(key)
                options.append((key, {"verb": "grasp_natural", "id": frag["id"]}))
    for obj in ground_objects(ctx.humans, ctx.xy):
        rigid_obj = obj["material"] in RIGID
        if (rigid_obj and not hands_free_rigid) or (not rigid_obj and not hands_free_soft):
            continue
        if mo.object_mass(obj) > carry_room:
            continue
        key = f"grasp:{object_class(obj)}|none"
        if key not in seen:
            seen.add(key)
            options.append((key, {"verb": "grasp_object", "id": obj["id"]}))

    for obj in ctx.held():
        options.append((f"release:{object_class(obj)}|none", {"verb": "release", "id": obj["id"]}))

    # Striking or seizing.
    tools = [None] + rigid
    for tool in tools:
        tclass = object_class(tool)
        if tool is not None:
            for frag in ctx.mcell_lithics()[:2]:
                options.append((f"strike:{_stone_class(frag)}|{tclass}", {"verb": "strike_stone", "tool": tool["id"], "natural": frag["id"]}))
            for obj in ground_objects(ctx.humans, ctx.xy):
                if obj["material"] == "stone":
                    options.append((f"strike:{object_class(obj)}|{tclass}", {"verb": "strike_stone", "tool": tool["id"], "object": obj["id"]}))
                    break
        for animal in ctx.animals_here()[:2]:
            if float(ctx.profile.get("development_scale", 1.0)) >= 0.5:
                options.append((f"strike:animal_{animal['species']}|{tclass}", {"verb": "capture", "tool": None if tool is None else tool["id"], "animal": animal["id"]}))

    # Edges and hands on producer and carcass material.
    edges = [None] + [t for t in rigid if _head_and_lever(t)[3] > 0.0]
    for tool in edges:
        tclass = object_class(tool)
        if available_kg("fresh_tissue", ctx.pcell, ctx.ccell) > 0.0:
            options.append((f"cut:fresh_tissue|{tclass}", {"verb": "cut_tissue", "tool": None if tool is None else tool["id"]}))
            if hands_free_soft:
                options.append((f"separate:tendon|{tclass}", {"verb": "extract_tendon", "tool": None if tool is None else tool["id"]}))
        if _mass(ctx.pcell.get("woody_elements_kg", {})) >= 0.2:
            if hands_free_soft:
                options.append((f"separate:bark|{tclass}", {"verb": "extract_bark", "tool": None if tool is None else tool["id"]}))
            if hands_free_rigid:
                options.append((f"cut:woody|{tclass}" if tool is not None else "break:woody|none", {"verb": "wood_piece", "tool": None if tool is None else tool["id"]}))
    if hands_free_soft and _mass(ctx.pcell.get("plant_elements_kg", {})) >= 0.05:
        options.append(("separate:plant_tissue|none", {"verb": "extract_plant_fiber"}))

    # Strand manipulations.
    strands = [o for o in soft if o["material"] == "fiber"]
    if hands_free_soft:  # pulling apart yields a second strand that must be held
        for strand in strands[:2]:
            options.append((f"separate:{object_class(strand)}|held", {"verb": "pull_apart", "id": strand["id"]}))
    if len(strands) >= 2:
        options.append(("twist:strands|held", {"verb": "twist"}))
    if len(strands) >= 4:
        options.append(("interlace:strands|held", {"verb": "interlace"}))
    if strands and len(rigid) >= 2:
        options.append((f"bind:{object_class(rigid[0])}+{object_class(rigid[1])}|strand", {"verb": "bind"}))
    for surface in [o for o in soft if o["material"] == "surface"]:
        options.append(("wear:surface|held", {"verb": "wear", "id": surface["id"]}))
        break

    # Existing bulk-wood primitives (G7), now reachable in live runs.
    if _mass(ctx.pcell.get("woody_elements_kg", {})) > 0.0:
        options.append(("apply_force:woody|none", {"verb": "pool", "sequence": ("apply_force",)}))
    if _mass(ctx.pcell.get("loose_material_elements_kg", {})) > 0.0:
        options.append(("arrange:loose_wood|none", {"verb": "pool", "sequence": ("arrange",)}))
    if _mass(ctx.pcell.get("arranged_material_elements_kg", {})) > 0.0:
        options.append(("separate:arranged_wood|none", {"verb": "pool", "sequence": ("separate",)}))
    return options


# ---------------------------------------------------------------------------
# Encounters with animals: approach and contact are physical stages.
#
# Declared encounter geometry (the grid declares no cell size): an animal in
# the agent's cell is visible but starts 10-60 m away. The agent must close to
# within reach (arm plus any held shaft) before it can grab or strike.
# - Stalk: each metre closed carries a detection hazard that grows with the
#   prey's perception and the agent's fatigue.
# - Chase: a detected animal flees toward cover 25 m away. The agent closes
#   the gap only if faster; sprinting is limited to 12 s. Prey in poor
#   condition run slower.
# - Contact: a held striking head kills if impact energy exceeds a mass-scaled
#   threshold; bare hands must grab and hold the animal.

ARM_REACH_M = 0.7
ENCOUNTER_MIN_M = 10.0
ENCOUNTER_MAX_M = 60.0
COVER_DISTANCE_M = 25.0
AGENT_SPRINT_M_S = 7.0
SPRINT_LIMIT_S = 12.0
ENCOUNTER_WALK_KCAL_PER_M = 0.04
ENCOUNTER_SPRINT_KCAL_PER_M = 0.15
KILL_J_PER_KG = 40.0


def resolve_encounter(
    *,
    capability: float,
    fatigue: float,
    reach_m: float,
    strike_energy_j: float,
    prey_mass_kg: float,
    prey_perception: int,
    prey_condition: float,
    draws: list[float],
) -> dict:
    """Resolve one approach. Returns stage outcome and distances covered."""
    separation = ENCOUNTER_MIN_M + (ENCOUNTER_MAX_M - ENCOUNTER_MIN_M) * draws[0]
    to_close = max(0.0, separation - reach_m)
    hazard = (0.02 + 0.02 * prey_perception) * (1.0 + fatigue)
    undetected_m = -math.log(max(1e-12, draws[1])) / hazard
    result = {"separation_m": separation, "walked_m": 0.0, "sprinted_m": 0.0, "sprint_s": 0.0, "contact": False}
    if undetected_m >= to_close:
        result["walked_m"] = to_close
        result["contact"] = True
    else:
        result["walked_m"] = undetected_m
        gap = to_close - undetected_m
        prey_speed = (6.0 + 1.0 * prey_perception) * (0.4 + 0.6 * max(0.0, min(1.0, prey_condition)))
        agent_speed = AGENT_SPRINT_M_S * max(0.0, capability)
        if agent_speed <= prey_speed:
            result["sprint_s"] = min(SPRINT_LIMIT_S, COVER_DISTANCE_M / prey_speed)
            result["sprinted_m"] = agent_speed * result["sprint_s"]
            result["outcome"] = "outrun"
            return result
        close_s = gap / (agent_speed - prey_speed)
        if close_s > min(SPRINT_LIMIT_S, COVER_DISTANCE_M / prey_speed):
            result["sprint_s"] = min(SPRINT_LIMIT_S, COVER_DISTANCE_M / prey_speed)
            result["sprinted_m"] = agent_speed * result["sprint_s"]
            result["outcome"] = "reached_cover"
            return result
        result["sprint_s"] = close_s
        result["sprinted_m"] = agent_speed * close_s
        result["contact"] = True
    kill_j = KILL_J_PER_KG * prey_mass_kg + 1.0
    if strike_energy_j > 0.0:
        killed = strike_energy_j * (0.5 + 0.5 * draws[2]) >= kill_j
    else:
        killed = draws[3] < 0.6 * max(0.0, capability) * (1.0 - 0.3 * max(0.0, min(1.0, prey_condition)))
    result["outcome"] = "kill" if killed else "contact_failed"
    return result


# ---------------------------------------------------------------------------
# Execution. Each returns an outcome with effort, injury and produced food.


def _find(humans: dict, object_id: str | None) -> dict | None:
    if object_id is None:
        return None
    for obj in humans["objects"]:
        if obj["id"] == object_id:
            return obj
    return None


def _held(ctx: Context, object_id: str | None) -> dict | None:
    """An object the acting agent is actually holding, or None.

    Physical-access guard: interactions may only use what is in hand. Live
    choice only ever offers held tools, so this never changes a live run; it
    makes a remote or stale reference fail closed instead of acting at a distance.
    """
    obj = _find(ctx.humans, object_id)
    if obj is None or obj.get("holder") != ctx.agent_id or obj.get("worn"):
        return None
    return obj


def _on_ground_here(ctx: Context, object_id: str | None) -> dict | None:
    """An unheld object lying in the acting agent's own cell, or None."""
    obj = _find(ctx.humans, object_id)
    if obj is None or obj.get("holder") is not None or (int(obj["x"]), int(obj["y"])) != ctx.xy:
        return None
    return obj


def _injure(ctx: Context, amount: float) -> float:
    ctx.human["injury"] = float(ctx.human.get("injury", 0.0)) + amount
    _bump(ctx.stats, "interaction_injury", amount)
    return amount


def _strike_load_test(ctx: Context, tool: dict, energy_j: float, out: dict) -> None:
    """Impact load passes through a binding; it may hold, slip or break."""
    if tool is None or tool["material"] != "assembly":
        return
    load = energy_j / 0.02 * 0.05
    result = mo.binding_load_result(tool, load, ctx.wetness())
    out["binding"] = result
    if result == "holds":
        return
    binder = tool["binder"]
    parts = list(tool["components"])
    ctx.humans["objects"].remove(tool)
    if result == "breaks":
        _bump(ctx.stats, "binding_load_breaks")
        first, second = mo.break_fiber(binder, ctx.draw("binder-break"), _new_id(ctx.humans, "fiber"))
        pieces = [first, second]
    else:
        _bump(ctx.stats, "binding_load_slips")
        pieces = [binder]
    # One part stays in hand; the rest falls.
    for index, part in enumerate(parts):
        ctx.humans["objects"].append(_place(part, ctx.xy[0], ctx.xy[1], ctx.agent_id if index == 0 else None))
    for piece in pieces:
        ctx.humans["objects"].append(_place(piece, ctx.xy[0], ctx.xy[1], None))


def _swing(ctx: Context, tool: dict | None) -> tuple[float, float, float, float, dict | None]:
    cap = _capability(ctx.human, ctx.profile)
    if tool is None:
        return 0.0, 1.0, 0.0, 0.0, None
    head_mass, lever, hardness, edge, fragment = _head_and_lever(tool)
    energy = mo.impact_energy_j(head_mass, WORK_PER_SWING_J * cap, HAND_SPEED_M_S * cap ** 0.5, lever)
    return energy, hardness, edge, head_mass, fragment


def _signature(obj: dict) -> str:
    # Putting something down is not preparation; picking it up is detected separately.
    return json.dumps({k: v for k, v in obj.items() if k not in {"history", "x", "y", "holder"}}, sort_keys=True, default=str)


def _merge_history(*histories: list[str]) -> list[str]:
    merged: list[str] = []
    for history in histories:
        for key in history:
            if key in merged:
                merged.remove(key)
            merged.append(key)
    return merged[-HISTORY_LENGTH:]


def execute(ctx: Context, key: str, spec: dict) -> dict:
    """Run one interaction and record it in the history of every object it
    made, shaped or picked up. Object history is how later benefit reaches the
    preparation that made it possible, however long ago that was."""
    before = {o["id"]: (_signature(o), o.get("history", []), o.get("holder")) for o in ctx.humans["objects"]}
    tool = _find(ctx.humans, spec.get("tool"))
    tool_history = list(tool.get("history", [])) if tool is not None else []
    out = _execute_physical(ctx, key, spec)
    out["tool_history"] = tool_history
    after_ids = {o["id"] for o in ctx.humans["objects"]}
    consumed = [hist for oid, (_, hist, _) in before.items() if oid not in after_ids]
    for obj in ctx.humans["objects"]:
        prior = before.get(obj["id"])
        if prior is None:
            obj["history"] = _merge_history(*consumed, tool_history, obj.get("history", []), [key])
        elif prior[0] != _signature(obj) or (obj.get("holder") == ctx.agent_id and prior[2] != ctx.agent_id):
            obj["history"] = _merge_history(prior[1], [key])
    return out


def _execute_physical(ctx: Context, key: str, spec: dict) -> dict:
    verb = spec["verb"]
    out = {"effort_kcal": 0.0, "injury": 0.0, "gain_kcal": 0.0, "event": verb}
    scale = max(0.1, float(ctx.profile.get("development_scale", 1.0)))
    humans = ctx.humans

    if verb == "grasp_natural":
        cell = ctx.mcell_lithics()
        frag = next((f for f in cell if f["id"] == spec["id"]), None)
        if frag is not None:
            cell.remove(frag)
            humans["objects"].append(_place({"id": frag["id"], "material": "stone", "fragment": frag}, ctx.xy[0], ctx.xy[1], ctx.agent_id))
            out["effort_kcal"] = 3.0 + 4.0 * float(frag["m"])

    elif verb == "grasp_object":
        obj = _on_ground_here(ctx, spec["id"])
        if obj is not None:
            obj["holder"] = ctx.agent_id
            out["effort_kcal"] = 3.0 + 4.0 * mo.object_mass(obj)

    elif verb == "release":
        obj = _held(ctx, spec["id"])
        if obj is not None:
            obj["holder"] = None
            out["effort_kcal"] = 1.0

    elif verb == "strike_stone":
        tool = _held(ctx, spec["tool"])
        if spec.get("natural"):
            cell = ctx.mcell_lithics()
            target_frag = next((f for f in cell if f["id"] == spec["natural"]), None)
            target_obj = None
        else:
            target_obj = _on_ground_here(ctx, spec.get("object"))
            target_frag = None if target_obj is None else target_obj["fragment"]
        if tool is not None and target_frag is not None:
            energy, hardness, edge, head_mass, head_frag = _swing(ctx, tool)
            target_hardness = mo.stone_props(target_frag)["hardness"]
            delivered = energy * min(1.0, hardness / target_hardness) * (0.5 + 0.5 * ctx.draw("strike", key))
            out["effort_kcal"] = 8.0 + 0.05 * energy
            pieces = mo.fracture(target_frag, delivered, ctx.draw("split", key), ctx.draw("edge", key), _new_id(humans, "stone"))
            if pieces is not None:
                core, flake = pieces
                _bump(ctx.stats, "fractures")
                if float(flake["s"]) >= 0.4:
                    _bump(ctx.stats, "sharp_flakes")
                if target_obj is None:
                    ctx.mcell_lithics().remove(target_frag)
                    humans["objects"].append(_place({"id": core["id"], "material": "stone", "fragment": core}, ctx.xy[0], ctx.xy[1], None))
                else:
                    target_obj["fragment"] = core
                humans["objects"].append(_place({"id": flake["id"], "material": "stone", "fragment": flake}, ctx.xy[0], ctx.xy[1], None))
                out["fracture"] = True
                if float(flake["s"]) >= 0.4 and ctx.draw("flying-chip", key) < 0.08:
                    out["injury"] += _injure(ctx, 0.02)
            # The hammer itself can break.
            if head_frag is not None and delivered >= mo.stone_props(head_frag)["fracture_energy_j"] * 1.2:
                hpieces = mo.fracture(head_frag, delivered, ctx.draw("hammer-split", key), ctx.draw("hammer-edge", key), _new_id(humans, "stone"))
                if hpieces is not None:
                    hcore, hflake = hpieces
                    head_frag.clear()
                    head_frag.update(hcore)
                    humans["objects"].append(_place({"id": hflake["id"], "material": "stone", "fragment": hflake}, ctx.xy[0], ctx.xy[1], None))
                    _bump(ctx.stats, "fractures")
            # Hands get hit: more likely when tired or when gripping an edge.
            fatigue = float(ctx.human.get("fatigue", 0.0))
            p_hurt = 0.04 + 0.10 * fatigue + 0.08 * (edge if tool["material"] == "stone" else 0.0)
            if ctx.draw("hand", key) < p_hurt:
                out["injury"] += _injure(ctx, 0.02 + 0.04 * ctx.draw("hand-amount", key))
            _strike_load_test(ctx, tool, energy, out)

    elif verb == "capture":
        animal = next(
            (a for a in ctx.consumers["animals"]
             if a["id"] == spec["animal"] and (int(a["x"]), int(a["y"])) == ctx.xy),
            None,
        )
        tool = _held(ctx, spec.get("tool"))
        if animal is not None:
            traits = trait_for(str(animal["species"]))
            energy, _, edge, _, _ = _swing(ctx, tool)
            enc = resolve_encounter(
                capability=_capability(ctx.human, ctx.profile),
                fatigue=float(ctx.human.get("fatigue", 0.0)),
                reach_m=ARM_REACH_M + _reach_m(tool),
                strike_energy_j=energy if tool is not None else 0.0,
                prey_mass_kg=_mass(animal["body_elements_kg"]),
                prey_perception=traits.perception_radius,
                prey_condition=min(1.0, float(animal["energy"]) / traits.reproduction_energy),
                draws=[ctx.draw("encounter", key, i) for i in range(4)],
            )
            _bump(ctx.stats, "capture_attempts")
            _bump(ctx.stats, f"encounter_{enc['outcome']}")
            out["encounter"] = enc
            out["effort_kcal"] = (5.0 + ENCOUNTER_WALK_KCAL_PER_M * enc["walked_m"] + ENCOUNTER_SPRINT_KCAL_PER_M * enc["sprinted_m"]) * scale
            ctx.human["fatigue"] = min(1.0, float(ctx.human.get("fatigue", 0.0)) + 0.004 * enc["sprint_s"])
            if enc["contact"] and traits.trophic_role == "predator" and ctx.draw("bite", key) < 0.6:
                out["injury"] += _injure(ctx, 0.05 + 0.10 * ctx.draw("bite-amount", key))
            if enc["outcome"] == "kill":
                killed = kill_animal(ctx.consumers, animal["id"], "agentus")
                if killed is not None:
                    _bump(ctx.stats, "captures")
                    ctx.produced["fresh_tissue"] = ctx.produced.get("fresh_tissue", 0.0) + _mass(killed["body_elements_kg"])
                    out["capture"] = True
            else:
                displace_animal(ctx.consumers, animal["id"], ctx.draw("flee", key))
                _bump(ctx.stats, "capture_escapes")
            if tool is not None and enc["contact"]:
                _strike_load_test(ctx, tool, energy, out)

    elif verb == "cut_tissue":
        tool = _held(ctx, spec.get("tool"))
        cap = _capability(ctx.human, ctx.profile)
        if tool is None:
            capacity = 0.0
        else:
            _, _, hardness, edge, frag = _head_and_lever(tool)
            capacity = mo.cutting_capacity(edge, hardness, 0.5, cap)
            if frag is not None:
                mo.edge_wear(frag, 0.5)
        bonus = 1.5 * capacity
        ctx.access_bonus["fresh_tissue"] = ctx.access_bonus.get("fresh_tissue", 0.0) + bonus
        out["effort_kcal"] = 10.0 * scale
        out["access_bonus_kg"] = bonus

    elif verb in {"extract_tendon", "extract_bark", "extract_plant_fiber"}:
        tool = _held(ctx, spec.get("tool"))
        cap = _capability(ctx.human, ctx.profile)
        capacity = 0.0
        if tool is not None:
            _, _, hardness, edge, frag = _head_and_lever(tool)
            target_h = 2.0 if verb == "extract_bark" else 0.5
            capacity = mo.cutting_capacity(edge, hardness, target_h, cap)
            if frag is not None:
                mo.edge_wear(frag, target_h)
        if verb == "extract_tendon":
            source, pool = "tendon", ctx.ccell["fresh_elements_kg"]
            length_scale = 0.3 + 0.7 * capacity
            if capacity < 0.1 and ctx.draw("tear", key) > 0.3:
                pool = None  # bare hands rarely free a tendon intact
        elif verb == "extract_bark":
            source, pool = "bark", ctx.pcell["woody_elements_kg"]
            length_scale = 0.4 + 0.6 * capacity
        else:
            source, pool = "plant", ctx.pcell["plant_elements_kg"]
            length_scale = 1.0
        out["effort_kcal"] = (18.0 if capacity < 0.1 else 10.0) * scale
        strands = 3 if source == "plant" else 1
        for i in range(strands):
            if pool is None:
                break
            free = len(ctx.soft_held())
            if free >= MAX_SOFT_IN_HAND:
                break
            u1, u2 = ctx.draw("fiber-len", key, i), ctx.draw("fiber-thick", key, i)
            spec_src = mo.FIBER_SOURCES[source]
            length = mo._span(spec_src["length_m"], u1) * length_scale
            thickness = mo._span(spec_src["thickness_mm"], u2)
            mass = mo.fiber_mass_for(source, length, thickness)
            available = _mass(pool)
            if available <= mass * 1.5:
                break
            taken = _debit_pool(pool, mass)
            fiber = mo.make_fiber(source, taken, u1, u2, _new_id(humans, "fiber"), length_scale)
            humans["objects"].append(_place(fiber, ctx.xy[0], ctx.xy[1], ctx.agent_id))
            _bump(ctx.stats, "fibers_extracted")

    elif verb == "wood_piece":
        tool = _held(ctx, spec.get("tool"))
        cap = _capability(ctx.human, ctx.profile)
        pool = ctx.pcell["woody_elements_kg"]
        if tool is None:
            max_mass, max_len = 0.6 * cap, 1.0
            out["effort_kcal"] = 30.0 * scale
            if ctx.draw("splinter", key) < 0.03:
                out["injury"] += _injure(ctx, 0.02)
        else:
            _, _, hardness, edge, frag = _head_and_lever(tool)
            capacity = mo.cutting_capacity(edge, hardness, 2.0, cap)
            energy, *_ = _swing(ctx, tool)
            max_mass = min(1.2, 0.6 * cap + 0.6 * capacity + energy / 400.0)
            max_len = 1.0 + 0.5 * capacity
            out["effort_kcal"] = 25.0 * scale
            if frag is not None:
                mo.edge_wear(frag, 2.0)
            _strike_load_test(ctx, tool, energy, out)
        mass = min(max_mass, _mass(pool) * 0.05)
        if mass >= 0.02 and len(ctx.rigid_held()) < MAX_RIGID_IN_HAND:
            taken = _debit_pool(pool, mass)
            piece = mo.make_wood_piece(taken, ctx.draw("wood-len", key), ctx.draw("wood-stiff", key), _new_id(humans, "wood"), max_len)
            humans["objects"].append(_place(piece, ctx.xy[0], ctx.xy[1], ctx.agent_id))
            _bump(ctx.stats, "wood_pieces")

    elif verb == "pull_apart":
        obj = _held(ctx, spec["id"])
        if obj is not None and len(ctx.soft_held()) < MAX_SOFT_IN_HAND:
            first, second = mo.break_fiber(obj, ctx.draw("pull", key), _new_id(humans, "fiber"))
            obj.clear()
            obj.update(_place(first, ctx.xy[0], ctx.xy[1], ctx.agent_id))
            humans["objects"].append(_place(second, ctx.xy[0], ctx.xy[1], ctx.agent_id))
            out["effort_kcal"] = 3.0

    elif verb == "twist":
        strands = sorted(
            (o for o in ctx.soft_held() if o["material"] == "fiber"),
            key=lambda o: (-float(o["length_m"]), o["id"]),
        )[:2]
        out["effort_kcal"] = 8.0 * scale
        if min(float(s["flexibility"]) for s in strands) < 0.3:
            stiff = min(strands, key=lambda s: float(s["flexibility"]))
            first, second = mo.break_fiber(stiff, ctx.draw("crack", key), _new_id(humans, "fiber"))
            stiff.clear()
            stiff.update(_place(first, ctx.xy[0], ctx.xy[1], ctx.agent_id))
            humans["objects"].append(_place(second, ctx.xy[0], ctx.xy[1], None))
        else:
            twisted = mo.twist(strands, _new_id(humans, "fiber"))
            for s in strands:
                humans["objects"].remove(s)
            humans["objects"].append(_place(twisted, ctx.xy[0], ctx.xy[1], ctx.agent_id))

    elif verb == "interlace":
        strands = sorted(
            (o for o in ctx.soft_held() if o["material"] == "fiber"),
            key=lambda o: (-float(o["length_m"]), o["id"]),
        )
        out["effort_kcal"] = 25.0 * scale
        surface = mo.interlace([{k: v for k, v in s.items() if k not in {"x", "y", "holder", "worn"}} for s in strands], _new_id(humans, "surface"))
        if surface is not None and float(surface["cohesion"]) >= 0.5:
            for s in strands:
                humans["objects"].remove(s)
            humans["objects"].append(_place(surface, ctx.xy[0], ctx.xy[1], ctx.agent_id))
            _bump(ctx.stats, "surfaces")
        else:
            out["unravelled"] = True

    elif verb == "bind":
        rigid = ctx.rigid_held()[:2]
        strands = sorted(
            (o for o in ctx.soft_held() if o["material"] == "fiber"),
            key=lambda o: (-mo.tensile_strength_n(o, ctx.wetness()), o["id"]),
        )
        out["effort_kcal"] = 15.0 * scale
        if len(rigid) == 2 and strands:
            binder = strands[0]
            cap = _capability(ctx.human, ctx.profile)
            tension = MAX_PULL_TENSION_N * cap * (0.4 + 0.6 * ctx.draw("pull-tension", key))
            strip = lambda o: {k: v for k, v in o.items() if k not in {"x", "y", "holder", "worn"}}
            result = mo.wrap_and_tighten(binder, [strip(r) for r in rigid], tension, ctx.wetness())
            out["bind_outcome"] = result["outcome"]
            if result["outcome"] == "bound":
                assembly = {
                    "id": _new_id(humans, "assembly"),
                    "material": "assembly",
                    "components": [strip(r) for r in rigid],
                    "binder": strip(binder),
                    "hold_n": round(float(result["hold_n"]), 10),
                }
                for o in rigid + [binder]:
                    humans["objects"].remove(o)
                humans["objects"].append(_place(assembly, ctx.xy[0], ctx.xy[1], ctx.agent_id))
                _bump(ctx.stats, "bindings")
            else:
                _bump(ctx.stats, "binding_failures")
                if result["outcome"] == "broke":
                    first, second = mo.break_fiber(binder, ctx.draw("bind-break", key), _new_id(humans, "fiber"))
                    binder.clear()
                    binder.update(_place(first, ctx.xy[0], ctx.xy[1], ctx.agent_id))
                    humans["objects"].append(_place(second, ctx.xy[0], ctx.xy[1], None))

    elif verb == "wear":
        obj = _held(ctx, spec["id"])
        if obj is not None:
            obj["worn"] = True
            out["effort_kcal"] = 4.0
            _bump(ctx.stats, "worn_surfaces")

    elif verb == "pool":
        updated, cell, trace = execute_live_sequence(spec["sequence"], ctx.human, ctx.pcell)
        ctx.human.update(updated)
        ctx.pcell.update(cell)
        out["effort_kcal"] = float(trace.get("effort_energy_kcal", 0.0))

    # Every attempt takes time and some effort, even one that changes nothing.
    # Without this floor a positive expectation for a costless repeat decays
    # toward zero without ever crossing it, and the repeat never stops.
    out["effort_kcal"] = max(float(out["effort_kcal"]), MIN_INTERACTION_KCAL * scale)
    ctx.human["energy"] = float(ctx.human["energy"]) - out["effort_kcal"]
    ctx.human["fatigue"] = min(1.0, float(ctx.human.get("fatigue", 0.0)) + FATIGUE_PER_INTERACTION)
    _bump(ctx.stats, "interaction_effort_kcal", out["effort_kcal"])
    _bump_map(ctx.stats, "interaction_counts", key.split("|")[0].split(":")[0], 1)
    return out


# ---------------------------------------------------------------------------
# Choice and learning


def choose(ctx: Context, options: list[tuple[str, dict]], step: int, hungry: bool) -> tuple[str, dict] | None:
    if not options:
        return None
    values = ctx.human["cognition"].get("affordance_values", {})
    untried = [o for o in options if o[0] not in values]
    explore_p = EXPLORE_HUNGRY if hungry else EXPLORE_SATED
    if untried and ctx.draw("explore", step) < explore_p:
        return untried[int(ctx.draw("explore-pick", step) * len(untried)) % len(untried)]
    known = [o for o in options if o[0] in values]
    positive = [o for o in known if float(values[o[0]]["v"]) > 0.0]
    if positive:
        picked = max(positive, key=lambda o: (float(values[o[0]]["v"]), o[0]))
        # Repeated use because it paid before: the measure of learned practice.
        _bump_map(ctx.stats, "exploit_by_key", picked[0], 1)
        users = dict(ctx.stats.get("exploit_agents", {}))
        users[picked[0]] = sorted(set(users.get(picked[0], [])) | {ctx.agent_id})
        ctx.stats["exploit_agents"] = users
        return picked
    if known and ctx.draw("retry", step) < RETRY_KNOWN:
        return known[int(ctx.draw("retry-pick", step) * len(known)) % len(known)]
    return None


def _update_value(values: dict, key: str, target: float, rate: float) -> None:
    entry = dict(values.get(key, {"n": 0, "v": 0.0}))
    if int(entry["n"]) == 0:
        entry["v"] = target
    else:
        entry["v"] = float(entry["v"]) + rate * (target - float(entry["v"]))
    entry["n"] = int(entry["n"]) + 1
    entry["v"] = round(float(entry["v"]), 10)
    values[key] = entry


def run_interactions(
    humans: dict,
    human: dict,
    profile: dict,
    pcell: dict,
    ccell: dict | None,
    lithic_cells: dict,
    wcell: dict,
    consumers: dict,
    epoch: int,
    hungry: bool,
) -> Context:
    """Perform up to MAX_INTERACTIONS_PER_TICK chosen interactions."""
    ctx = Context(humans, human, profile, pcell, ccell, lithic_cells, wcell, consumers, epoch)
    for step in range(MAX_INTERACTIONS_PER_TICK):
        if float(human.get("fatigue", 0.0)) > 0.8:
            break
        picked = choose(ctx, enumerate_affordances(ctx), step, hungry)
        if picked is None:
            break
        key, spec = picked
        injury_before = float(human.get("injury", 0.0))
        out = execute(ctx, key, spec)
        out["injury"] = float(human.get("injury", 0.0)) - injury_before
        ctx.performed.append((key, out))
    return ctx


def learn_from_tick(ctx: Context, intake: list[dict]) -> None:
    """Update interaction and food expectations from what was experienced."""
    cognition = dict(ctx.human["cognition"])
    basal = max(1e-9, float(ctx.profile["basal_energy_kcal_per_tick"]))
    values = dict(cognition.get("affordance_values", {}))
    food_values = dict(cognition.get("food_values", {}))

    # Food kinds: experienced net value per kg of what was actually ingested.
    for rec in intake:
        if rec["kg"] <= 0.0:
            continue
        observed = (rec["kcal"] - rec["handling_kcal"]) / rec["kg"] - rec["hazard"] * basal * 2.0 / rec["kg"]
        prior = food_values.get(rec["kind"])
        food_values[rec["kind"]] = round(observed if prior is None else float(prior) + FOOD_LEARNING_RATE * (observed - float(prior)), 10)

    # Attribute food gains to the interactions that made them possible.
    kcal_by_kind: dict[str, float] = {}
    kg_by_kind: dict[str, float] = {}
    for rec in intake:
        kcal_by_kind[rec["kind"]] = kcal_by_kind.get(rec["kind"], 0.0) + rec["kcal"] - rec["handling_kcal"]
        kg_by_kind[rec["kind"]] = kg_by_kind.get(rec["kind"], 0.0) + rec["kg"]
    hand_access = float(FOOD_KINDS["fresh_tissue"]["hand_access_kg"]) * max(0.1, float(ctx.profile.get("development_scale", 1.0)))
    trace = list(cognition.get("trace", []))
    for key, out in ctx.performed:
        gain = 0.0
        if out.get("capture") and kg_by_kind.get("fresh_tissue", 0.0) > 0.0:
            gain += max(0.0, kcal_by_kind["fresh_tissue"]) * min(1.0, ctx.produced.get("fresh_tissue", 0.0) / max(1e-9, kg_by_kind["fresh_tissue"]))
        if out.get("access_bonus_kg", 0.0) > 0.0 and kg_by_kind.get("fresh_tissue", 0.0) > 0.0:
            share = out["access_bonus_kg"] / (hand_access + ctx.access_bonus.get("fresh_tissue", 0.0))
            gain += max(0.0, kcal_by_kind["fresh_tissue"]) * share
        reward = (gain - out["effort_kcal"]) / basal - out["injury"] * 2.0
        _update_value(values, key, reward, VALUE_LEARNING_RATE)
        if gain > 0.0:
            _credit_preparation(values, trace, out.get("tool_history", []), gain / basal)
            observe_outcome(ctx, key, reward)
        trace = (trace + [key])[-TRACE_LENGTH:]

    for rec in intake:
        _bump_map(ctx.stats, "intake_kg_by_kind", rec["kind"], round(rec["kg"], 10))
        _bump_map(ctx.stats, "intake_kcal_by_kind", rec["kind"], round(rec["kcal"], 6))
        _bump(ctx.stats, "ingestion_hazard", rec["hazard"])

    cognition["affordance_values"] = values
    cognition["food_values"] = food_values
    cognition["trace"] = trace
    ctx.human["cognition"] = cognition
    observe_food(ctx, intake)


def _credit_preparation(values: dict, trace: list[str], tool_history: list[str], gain_basal: float) -> None:
    """Pass a realized benefit back to the actions that prepared it.

    Two routes: recent actions (a decaying time trace) and the recorded history
    of the object that was used, regardless of how long ago it was made. A key
    reached by both routes is credited once, at the larger share.
    """
    shares: dict[str, float] = {}
    for depth, prior_key in enumerate(reversed(trace), start=1):
        shares[prior_key] = max(shares.get(prior_key, 0.0), TRACE_DECAY ** depth)
    for depth, prior_key in enumerate(reversed(tool_history)):
        shares[prior_key] = max(shares.get(prior_key, 0.0), HISTORY_DECAY ** depth)
    for prior_key, share in sorted(shares.items()):
        if prior_key in values:
            entry = dict(values[prior_key])
            entry["v"] = round(float(entry["v"]) + VALUE_LEARNING_RATE * share * gain_basal, 10)
            values[prior_key] = entry


def observe_outcome(ctx: Context, key: str, reward: float) -> None:
    """Agents sharing the cell see an interaction succeed and update their own
    expectation of it (declared assumption: a visible, beneficial outcome is
    observable; failures and internal costs are not transmitted)."""
    if reward <= 0.0:
        return
    for peer in ctx.humans["humans"]:
        if peer is ctx.human or "cognition" not in peer:
            continue
        if (int(peer["x"]), int(peer["y"])) != ctx.xy:
            continue
        cognition = dict(peer["cognition"])
        values = dict(cognition.get("affordance_values", {}))
        entry = dict(values.get(key, {"n": 0, "v": 0.0}))
        entry["v"] = round(float(entry["v"]) + OBSERVATION_RATE * (reward - float(entry["v"])) * (1.0 if int(entry["n"]) == 0 else VALUE_LEARNING_RATE), 10)
        values[key] = entry
        cognition["affordance_values"] = values
        peer["cognition"] = cognition
        _bump_map(ctx.stats, "observed_transmissions", key, 1)


def observe_food(ctx: Context, intake: list[dict]) -> None:
    """Agents sharing the cell see what another eats repeatedly without harm and
    may adopt a cautious prior for a kind they have never valued."""
    for rec in intake:
        if rec["kg"] <= 0.0 or rec.get("hazard", 0.0) > 0.0 or rec["kcal"] <= 0.0:
            continue
        for peer in ctx.humans["humans"]:
            if peer is ctx.human or "cognition" not in peer:
                continue
            if (int(peer["x"]), int(peer["y"])) != ctx.xy:
                continue
            known = peer["cognition"].get("food_values", {})
            if rec["kind"] in known:
                continue
            cognition = dict(peer["cognition"])
            food_values = dict(known)
            food_values[rec["kind"]] = round(OBSERVATION_RATE * rec["kcal"] / rec["kg"], 10)
            cognition["food_values"] = food_values
            peer["cognition"] = cognition
            _bump_map(ctx.stats, "observed_food_adoptions", rec["kind"], 1)


def credit_worn_benefit(humans: dict, human: dict, saving_kcal: float, profile: dict) -> None:
    """Warmth retained by worn material is an experienced benefit. It reinforces
    wearing and the preparation recorded in the worn object's history."""
    if saving_kcal <= 0.0 or "cognition" not in human:
        return
    basal = max(1e-9, float(profile["basal_energy_kcal_per_tick"]))
    cognition = dict(human["cognition"])
    values = dict(cognition.get("affordance_values", {}))
    for obj in humans.get("objects", []):
        if obj.get("holder") == human["id"] and obj.get("worn"):
            _credit_preparation(values, [], list(obj.get("history", [])), saving_kcal / basal)
    cognition["affordance_values"] = values
    human["cognition"] = cognition
    stats = humans.setdefault("capacity_stats", empty_stats())
    _bump(stats, "insulation_saving_kcal", saving_kcal)


def choose_food_samples(human: dict, pcell: dict, ccell: dict | None, epoch: int, hungry: bool) -> tuple[str, ...]:
    """Bounded exploration of unknown kinds present here: at most one per tick."""
    known = human["cognition"].get("food_values", {})
    unknown = [k for k in FOOD_KINDS if k not in known and available_kg(k, pcell, ccell) > 0.0]
    if not unknown:
        return ()
    p = FOOD_SAMPLE_HUNGRY if hungry else FOOD_SAMPLE_SATED
    if mo.unit_draw(human["id"], epoch, "food-sample") >= p:
        return ()
    return (unknown[int(mo.unit_draw(human["id"], epoch, "food-pick") * len(unknown)) % len(unknown)],)


# ---------------------------------------------------------------------------
# World effects on objects each tick


def weather_objects(humans: dict, pcells: dict, wcells: dict, epoch: int) -> None:
    """Fire and decay act on objects wherever they are."""
    survivors = []
    for obj in humans.get("objects", []):
        xy = (int(obj["x"]), int(obj["y"]))
        pcell = pcells[xy]
        intensity = float(pcell.get("fire_intensity", 0.0))
        detritus = pcell["detritus_elements_kg"]
        held = obj.get("holder") is not None
        decay = ORGANIC_DECAY_HELD if held else ORGANIC_DECAY_GROUND
        burn = 0.1 * intensity if (intensity > 0.2 and not held) else 0.0
        _degrade(obj, decay + burn, detritus)
        if obj["material"] == "stone" and intensity > 0.2 and not held:
            fragment, flake = mo.heat_stone(obj["fragment"], intensity, mo.unit_draw(obj["id"], epoch, "heat"), f"{obj['id']}-h{epoch}")
            obj["fragment"] = fragment
            if flake is not None:
                survivors.append(_place({"id": flake["id"], "material": "stone", "fragment": flake}, xy[0], xy[1], None))
        if obj["material"] != "stone" and mo.object_lithic_mass(obj) <= 0.0 and mo.object_mass(obj) < 1e-7:
            for symbol, amount in mo.object_elements(obj).items():
                detritus[symbol] = float(detritus.get(symbol, 0.0)) + float(amount)
            continue
        survivors.append(obj)
    humans["objects"] = survivors


def _degrade(obj: dict, fraction: float, detritus: dict) -> None:
    if fraction <= 0.0:
        return
    material = obj["material"]
    if material in {"fiber", "wood"}:
        for symbol in sorted(obj["elements_kg"]):
            amount = float(obj["elements_kg"][symbol]) * fraction
            obj["elements_kg"][symbol] = float(obj["elements_kg"][symbol]) - amount
            detritus[symbol] = float(detritus.get(symbol, 0.0)) + amount
        if material == "fiber":
            obj["integrity"] = round(max(0.0, float(obj.get("integrity", 1.0)) * (1.0 - 2.0 * fraction)), 10)
    elif material == "surface":
        for strand in obj["strands"]:
            _degrade(strand, fraction, detritus)
        obj["cohesion"] = round(max(0.0, float(obj["cohesion"]) * (1.0 - fraction)), 10)
    elif material == "assembly":
        for part in obj["components"]:
            _degrade(part, fraction, detritus)
        _degrade(obj["binder"], fraction, detritus)
