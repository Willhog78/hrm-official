"""Read-only observer shared by the smoke and diagnostic tiers.

`run_observed(seed, arm, days)` runs one production simulation and returns
outcome metrics plus integrity and pathology checks. The observer wraps a few
production functions to *look* at their inputs and outputs; every wrapper
returns exactly what the original returned and writes nothing to the world.
It is independent of the guards inside the production code: it re-derives
physical access from the state it sees, so a regression in those guards shows
up here.

Arms are the multiseed arms (`v0`, `v1`, `plant_diet`, `no_interactions`,
`no_recall`, `null`, each optionally `-nothirst`), then optionally
`-preg106` (G10.6 integrity off), `-g104obs` (G10.4 observation) and `@<physiology>`, e.g. `v1-preg106@reference-v2`.

Checks are split into:
  FAIL: broken invariants (crash, NaN, negative mass, ledger, conservation,
        remote acquisition, duplicate kill, interaction budget, thirst rule
        violations, a no-op habit repeated as if it paid).
  WARN: known or suspected behavioural problems worth watching (starving
        beside food, fatigue saturation, high no-op share).
"""

from __future__ import annotations

import math
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "src", ROOT, ROOT / "experiments" / "genesis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import hrm_genesis.human.biology as biology  # noqa: E402
import hrm_genesis.human.interactions as cap  # noqa: E402
import hrm_genesis.human.planning as planning  # noqa: E402
from hrm_genesis import GenesisConfig, GenesisSimulation  # noqa: E402
from hrm_genesis.ecology.animals import consumer_element_totals, consumer_water_total_kg  # noqa: E402
from hrm_genesis.ecology.plants import ecology_element_totals  # noqa: E402
from hrm_genesis.human import human_element_totals, human_water_total_kg  # noqa: E402
from hrm_genesis.matter.pools import total_elements, total_water  # noqa: E402
from run_agentus_capacity_multiseed import config_for  # noqa: E402

# A habit that keeps failing must extinguish: one agent repeating the same
# no-op as a learned habit this many times is a superstition loop.
NOOP_HABIT_LIMIT = 10
# Relative tolerance for whole-world element and water balance.
CONSERVATION_REL_TOL = 1e-6
FATIGUE_BLOCK = 0.8  # interactions stop above this (interactions.run_interactions)


PRE_G10_6 = "-preg106"  # arm suffix: behavioural/locomotion integrity off
LEGACY_OBSERVATION = "-g104obs"  # arm suffix: G10.4 observation (copies reward and energy yield)
NO_MEMORY = "-nomem"  # arm suffix: no witnessed-event memory (G10.7a step 2 off)
FIFO_MEMORY = "-fifo"  # arm suffix: step-2 newest-first retention (G10.7a step 2.5 off)
NO_IMITATION = "-noimit"  # arm suffix: no imitation (G10.7a step 3 off)


def build_config(seed: str, arm: str) -> GenesisConfig:
    base, _, physiology = arm.partition("@")
    no_imitation = base.endswith(NO_IMITATION)
    base = base.removesuffix(NO_IMITATION)
    fifo = base.endswith(FIFO_MEMORY)
    base = base.removesuffix(FIFO_MEMORY)
    no_memory = base.endswith(NO_MEMORY)
    base = base.removesuffix(NO_MEMORY)
    legacy_observation = base.endswith(LEGACY_OBSERVATION)
    base = base.removesuffix(LEGACY_OBSERVATION)
    integrity = not base.endswith(PRE_G10_6)
    config = config_for(seed, base.removesuffix(PRE_G10_6))
    overrides = {}
    if legacy_observation:
        overrides["agentus_observation_model"] = "g10.4-legacy"
    if no_memory:
        overrides["agentus_event_memory_enabled"] = False
    if fifo:
        overrides["agentus_event_memory_retention"] = "fifo"
    if no_imitation:
        overrides["agentus_imitation_enabled"] = False
    if physiology:
        overrides["agentus_physiology_version"] = physiology
    if not integrity:
        overrides["agentus_behavior_integrity_enabled"] = False
    if overrides:
        config = GenesisConfig(**{**config.__dict__, **overrides})
    return config


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


# ---------------------------------------------------------------------------
# Numeric scan: NaN/inf anywhere, negative values in any mass field.


def _scan(node, path: str, in_mass: bool, found: Counter, examples: list) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            k = str(key)
            _scan(value, k, in_mass or k.endswith("_kg"), found, examples)
    elif isinstance(node, (list, tuple)):
        for value in node:
            _scan(value, path, in_mass, found, examples)
    elif isinstance(node, float):
        if not math.isfinite(node):
            found["non_finite"] += 1
            if len(examples) < 5:
                examples.append(f"non-finite {path}")
        elif in_mass and node < -1e-9:
            found["negative_mass"] += 1
            if len(examples) < 5:
                examples.append(f"negative {path}={node:.3g}")


# ---------------------------------------------------------------------------
# Whole-world balance (same accounting as the G5 gate).


def conservation_errors(sim: GenesisSimulation) -> dict[str, float]:
    matter = sim.matter_state()
    parts = (
        total_elements(matter["cells"]),
        ecology_element_totals(sim.ecology_state()),
        consumer_element_totals(sim.consumer_state()),
        human_element_totals(sim.human_state()),
    )
    initial = {k: float(v) for k, v in matter["initial_elements_kg"].items()}
    symbols = sorted(set(initial).union(*parts))
    element_error = max(abs(sum(p.get(s, 0.0) for p in parts) - initial.get(s, 0.0)) for s in symbols)
    element_scale = max(1.0, sum(initial.values()))
    stored = total_water(matter["cells"]) + consumer_water_total_kg(sim.consumer_state()) + human_water_total_kg(sim.human_state())
    expected = float(matter["initial_water_kg"]) + float(matter["water_input_kg"]) - float(matter["water_output_kg"])
    lithic = None
    if "initial_lithic_kg" in matter:
        lithic = abs(cap.lithic_inventory_kg(matter, sim.human_state()) - float(matter["initial_lithic_kg"]))
    return {
        "element_rel_error": element_error / element_scale,
        "water_rel_error": abs(stored - expected) / max(1.0, expected),
        "lithic_abs_error_kg": lithic,
    }


# ---------------------------------------------------------------------------
# Wrappers (measurement only).


class Observer:
    def __init__(self) -> None:
        self.c = Counter()
        self.examples: list[str] = []
        self.killed: set[str] = set()
        self.per_agent_day: Counter = Counter()
        self.noop_keys: Counter = Counter()
        self.exploited_noops_by_agent_key: Counter = Counter()
        self._exploit_pick: dict[str, str] = {}
        self._originals: list[tuple[object, str, object]] = []

    def _note(self, kind: str, text: str) -> None:
        self.c[kind] += 1
        if len(self.examples) < 12:
            self.examples.append(f"{kind}: {text}")

    # -- physical access before each interaction ---------------------------
    def _check_access(self, ctx, key: str, spec: dict) -> None:
        verb = spec["verb"]
        xy = (int(ctx.human["x"]), int(ctx.human["y"]))
        objects = {o["id"]: o for o in ctx.humans.get("objects", [])}
        here_lithics = {f["id"] for f in ctx.lithic_cells.get(f"{xy[0]},{xy[1]}", [])}

        def held(oid):
            o = objects.get(oid)
            return o is not None and o.get("holder") == ctx.agent_id

        def on_ground_here(oid):
            o = objects.get(oid)
            return o is not None and o.get("holder") is None and (int(o["x"]), int(o["y"])) == xy

        tool = spec.get("tool")
        if tool is not None and not held(tool):
            self._note("FAIL_remote_tool", f"{ctx.agent_id} {key} tool={tool}")
        if verb == "grasp_natural" and spec["id"] not in here_lithics:
            self._note("FAIL_remote_pickup", f"{ctx.agent_id} {key} {spec['id']}")
        elif verb == "grasp_object" and not on_ground_here(spec["id"]):
            self._note("FAIL_remote_pickup", f"{ctx.agent_id} {key} {spec['id']}")
        elif verb in {"release", "pull_apart", "wear"} and not held(spec["id"]):
            self._note("FAIL_object_not_held", f"{ctx.agent_id} {key} {spec['id']}")
        elif verb == "strike_stone":
            if "natural" in spec and spec["natural"] not in here_lithics:
                self._note("FAIL_remote_target", f"{ctx.agent_id} {key}")
            if "object" in spec and not (held(spec["object"]) or on_ground_here(spec["object"])):
                self._note("FAIL_remote_target", f"{ctx.agent_id} {key}")
        elif verb == "capture":
            animal = next((a for a in ctx.consumers.get("animals", []) if a["id"] == spec["animal"]), None)
            if animal is None or (int(animal["x"]), int(animal["y"])) != xy:
                self._note("FAIL_remote_capture", f"{ctx.agent_id} {key} {spec['animal']}")
            if spec["animal"] in self.killed:
                self._note("FAIL_duplicate_kill", f"{spec['animal']} targeted after being killed")

    @staticmethod
    def _local_digest(ctx) -> tuple:
        xy = (int(ctx.human["x"]), int(ctx.human["y"]))
        objs = tuple(sorted(
            (o["id"], o.get("holder"), bool(o.get("worn")), cap._signature(o))
            for o in ctx.humans.get("objects", [])
            if o.get("holder") == ctx.agent_id or (int(o["x"]), int(o["y"])) == xy
        ))
        lith = tuple(sorted((f["id"], round(float(f["m"]), 9)) for f in ctx.lithic_cells.get(f"{xy[0]},{xy[1]}", [])))
        pools = tuple(round(_mass(v), 9) for k, v in sorted(ctx.pcell.items()) if k.endswith("_elements_kg"))
        carcass = () if ctx.ccell is None else (round(_mass(ctx.ccell.get("fresh_elements_kg", {})), 9),)
        animals = tuple(sorted((a["id"], a["x"], a["y"]) for a in ctx.consumers.get("animals", [])))
        return objs, lith, pools, carcass, animals, round(float(ctx.human.get("injury", 0.0)), 9)

    def install(self) -> None:
        obs = self
        original_execute = cap.execute
        original_choose = cap.choose
        original_thirst = planning._thirst_destination

        def execute(ctx, key, spec):
            obs._check_access(ctx, key, spec)
            before = obs._local_digest(ctx)
            out = original_execute(ctx, key, spec)
            obs.c["interactions"] += 1
            obs.per_agent_day[(ctx.agent_id, ctx.epoch)] += 1
            if spec["verb"] == "capture" and out.get("capture"):
                if spec["animal"] in obs.killed:
                    obs._note("FAIL_duplicate_kill", spec["animal"])
                obs.killed.add(spec["animal"])
                obs.c["kills"] += 1
            if obs._local_digest(ctx) == before:
                obs.c["noop_interactions"] += 1
                obs.noop_keys[key] += 1
                if obs._exploit_pick.get(ctx.agent_id) == key:
                    obs.c["exploited_noops"] += 1
                    obs.exploited_noops_by_agent_key[(ctx.agent_id, key)] += 1
            obs._exploit_pick.pop(ctx.agent_id, None)
            return out

        def choose(ctx, options, step, hungry):
            before = sum(ctx.stats.get("exploit_by_key", {}).values())
            picked = original_choose(ctx, options, step, hungry)
            if picked is not None and sum(ctx.stats.get("exploit_by_key", {}).values()) > before:
                obs._exploit_pick[ctx.agent_id] = picked[0]
                obs.c["exploit_choices"] += 1
            return picked

        def thirst(perception, cognition, forage_need, reserve_fraction):
            result = original_thirst(perception, cognition, forage_need, reserve_fraction)
            if result is not None and "water_need_kg" in perception:
                obs.c["thirst_moves"] += 1
                ox, oy = map(int, perception["origin"])
                visible = {(int(c["x"]), int(c["y"])): c for c in perception["cells"]}
                if abs(result[0] - ox) + abs(result[1] - oy) > 1:
                    obs._note("FAIL_thirst_move_beyond_one_step", f"{(ox, oy)}->{result}")
                if result not in visible:
                    obs._note("FAIL_thirst_target_not_perceived", f"{(ox, oy)}->{result}")
                hungry = forage_need > 0.0 and reserve_fraction < 0.75
                if hungry and float(perception["energy_days"]) < float(perception["hydration_days"]):
                    target = visible.get(result, {})
                    if float(target.get("expected_food_kg", target.get("food_kg", 0.0))) < forage_need:
                        obs._note("FAIL_thirst_over_more_urgent_hunger", f"at {(ox, oy)}")
            return result

        for module, name, fn in ((cap, "execute", execute), (cap, "choose", choose), (planning, "_thirst_destination", thirst)):
            self._originals.append((module, name, getattr(module, name)))
            setattr(module, name, fn)

    def uninstall(self) -> None:
        for module, name, fn in reversed(self._originals):
            setattr(module, name, fn)
        self._originals.clear()


# ---------------------------------------------------------------------------
# One observed run.


def _death_context(cause: str, person: dict, wet: dict, food: dict, profile: dict) -> str:
    x, y = int(person["x"]), int(person["y"])
    if cause in {"energy", "low_body_mass"}:
        return "food_in_own_cell" if food.get((x, y), 0.0) >= 5.0 else "no_food_in_own_cell"
    near = [(x + dx, y + dy) for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))]
    need_w = float(profile["water_capacity_kg"]) - float(person["body_water_kg"]) + float(profile["water_loss_per_tick_kg"])
    if any(wet.get(xy, 0.0) >= need_w for xy in near):
        return "water_visible"
    remembered = person.get("cognition", {}).get("memory", {}).get("locations", {})
    if any(float(v.get("water_kg", 0.0)) >= need_w for v in remembered.values()):
        return "water_remembered"
    return "no_water_known"


def _memory_summary(people: list[dict], stats: dict, independent_age: int) -> dict:
    """What living agents hold in witnessed-event memory at the end of a run."""
    held = [p["cognition"].get("witnessed", []) for p in people]
    with_memory = [m for m in held if m]
    dependents = [p["cognition"].get("witnessed", []) for p in people if int(p["age_ticks"]) < independent_age]
    n = max(1, len(with_memory))
    return {
        "events_witnessed": int(stats.get("witnessed_events", 0)),
        "top_acts": dict(Counter(stats.get("witnessed_by_act", {})).most_common(5)),
        "agents_with_memory": len(with_memory),
        "mean_events_held": round(sum(len(m) for m in with_memory) / n, 1),
        "mean_distinct_acts": round(sum(len({e["act"] for e in m}) for m in with_memory) / n, 1),
        "mean_distinct_actors": round(sum(len({e["actor"] for e in m}) for m in with_memory) / n, 1),
        "non_eating_events_held": sum(1 for m in with_memory for e in m if not e["act"].startswith("eat:")),
        "full_memories": sum(1 for m in with_memory if len(m) >= 32),
        "dependents_with_memory": sum(1 for m in dependents if m),
    }


def _check_dependents(before: dict, after: dict, independent_age: int, observer: Observer) -> None:
    """A dependent may move with its caregiver (carried) or one cell on its own."""
    start = {p["id"]: p for p in before["humans"]}
    for child in after["humans"]:
        prev = start.get(child["id"])
        if prev is None or not prev.get("caregiver_id") or int(prev["age_ticks"]) >= independent_age:
            continue
        observer.c["dependent_days"] += 1
        carer_before = start.get(prev["caregiver_id"])
        carried = carer_before is not None and (prev["x"], prev["y"]) == (carer_before["x"], carer_before["y"])
        step = abs(int(child["x"]) - int(prev["x"])) + abs(int(child["y"]) - int(prev["y"]))
        if not carried and step > 1:
            observer._note("FAIL_dependent_teleport", f"{child['id']} moved {step} cells alone")
        if not child.get("caregiver_present", True):
            observer.c["dependent_days_apart"] += 1


def run_observed(seed: str, arm: str, days: int, scan_every: int = 1) -> dict:
    started = time.perf_counter()
    observer = Observer()
    observer.install()
    result: dict = {"seed": seed, "arm": arm, "days": days}
    try:
        sim = GenesisSimulation(build_config(seed, arm))
        result["fingerprint"] = sim.config.fingerprint()[:12]
        state = sim.human_state()
        profile = state["physiology_profile"]
        maturity = int(profile["maturity_ticks"])
        independent = int(profile["independent_feeding_age_ticks"])
        numeric: Counter = Counter()
        numeric_examples: list[str] = []
        deaths: Counter = Counter()
        fatigue = Counter()
        seen: set[str] = set()
        alive_min = len(state["humans"])
        founders = len(state["humans"])
        for day in range(days):
            before = sim.human_state()
            wet = {(c["x"], c["y"]): float(c["surface_water_kg"]) + float(c["soil_water_kg"]) for c in sim.matter_state()["cells"]}
            food = {(c["x"], c["y"]): _mass(c["plant_elements_kg"]) + _mass(c["seed_elements_kg"]) for c in sim.ecology_state()["cells"]}
            sim.run(1)
            after = sim.human_state()
            alive_min = min(alive_min, len(after["humans"]))
            _check_dependents(before, after, independent, observer)
            for person in after["humans"]:
                f = float(person.get("fatigue", 0.0))
                fatigue["agent_days"] += 1
                fatigue["blocked_days"] += f > FATIGUE_BLOCK
            if scan_every and (day % scan_every == 0 or day == days - 1):
                for part in (after, sim.matter_state(), sim.ecology_state(), sim.consumer_state()):
                    _scan(part, "", False, numeric, numeric_examples)
            people = {p["id"]: p for p in before["humans"]}
            for record in after.get("death_records", []):
                if record["id"] in seen or record["id"] not in people:
                    seen.add(record["id"])
                    continue
                seen.add(record["id"])
                person = people[record["id"]]
                stage = "adult" if int(person["age_ticks"]) >= maturity else (
                    "juvenile" if int(person["age_ticks"]) >= independent else "dependent")
                deaths[f"{record['cause']}|{stage}|{_death_context(record['cause'], person, wet, food, profile)}"] += 1
        final = sim.human_state()
        result["ledger_digest"] = sim.ledger.digest()
        stats = final.get("capacity_stats", {})
        ledger_valid = sim.ledger.verify_chain()
        conservation = conservation_errors(sim)
        people = final["humans"]
        food_known = Counter(k for p in people for k, v in p.get("cognition", {}).get("food_values", {}).items() if float(v) > 0.0)
        learned = Counter(k for p in people for k, e in p.get("cognition", {}).get("affordance_values", {}).items() if float(e["v"]) > 0.0)
        consumers = sim.consumer_state()
        result.update({
            "alive": len(people),
            "alive_min": alive_min,
            "founders": founders,
            "adults": sum(1 for p in people if int(p["age_ticks"]) >= maturity),
            "births": int(final.get("cumulative_births", 0)),
            "deaths_by_cause": dict(final.get("cumulative_deaths_by_cause", {})),
            "death_context": dict(deaths),
            "hunting": {
                "encounters": {k: stats.get(f"encounter_{k}", 0) for k in ("kill", "contact_failed", "outrun", "reached_cover")},
                "capture_attempts": stats.get("capture_attempts", 0),
                "captures": stats.get("captures", 0),
                "fresh_tissue_kg": round(stats.get("intake_kg_by_kind", {}).get("fresh_tissue", 0.0), 3),
                "animals_end": len(consumers.get("animals", [])),
            },
            "intake_kg_by_kind": {k: round(v, 2) for k, v in stats.get("intake_kg_by_kind", {}).items()},
            "food_kinds_valued": dict(food_known),
            "interaction_counts": dict(stats.get("interaction_counts", {})),
            "repeated_use": dict(stats.get("exploit_by_key", {})),
            "repeated_use_agents": {k: len(v) for k, v in stats.get("exploit_agents", {}).items()},
            "observed_transmissions": dict(stats.get("observed_transmissions", {})),
            "observed_food_adoptions": dict(stats.get("observed_food_adoptions", {})),
            "observed_ingestions": dict(stats.get("observed_ingestions", {})),
            "food_learned_after_observation": dict(stats.get("food_learned_after_observation", {})),
            "memory": _memory_summary(people, stats, independent),
            "imitation": {
                "tries": dict(stats.get("imitation_tries", {})),
                "paid": dict(stats.get("imitation_paid", {})),
                "unpaid": dict(stats.get("imitation_unpaid", {})),
                "sources": {k: len(v) for k, v in stats.get("imitated_from", {}).items()},
                # Practices now valued by living agents that some agent first tried by imitation.
                "valued_after_imitation": dict(Counter(
                    k for p in people for k, e in p.get("cognition", {}).get("affordance_values", {}).items()
                    if float(e["v"]) > 0.0 and k in stats.get("imitated_from", {}))),
            },
            "learned_positive_living": dict(learned.most_common(8)),
            "ledger_valid": ledger_valid,
            "conservation": conservation,
            "observer": dict(observer.c),
            "max_interactions_per_agent_day": max(observer.per_agent_day.values(), default=0),
            "top_noop_keys": dict(observer.noop_keys.most_common(4)),
            "max_noop_habit_repeats": max(observer.exploited_noops_by_agent_key.values(), default=0),
            "noop_habits": {f"{a}|{k}": n for (a, k), n in observer.exploited_noops_by_agent_key.most_common(3)},
            "fatigue_blocked_share": round(fatigue["blocked_days"] / max(1, fatigue["agent_days"]), 3),
            "numeric": dict(numeric),
            "examples": numeric_examples + observer.examples,
        })
    except Exception as exc:  # a crash is a result, not a stop
        import traceback
        result["crash"] = f"{type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc(limit=6)
    finally:
        observer.uninstall()
    result["seconds"] = round(time.perf_counter() - started, 1)
    result["checks"] = evaluate(result)
    return result


def evaluate(r: dict) -> dict[str, list[str]]:
    """Turn one run's measurements into FAIL and WARN lines."""
    fails: list[str] = []
    warns: list[str] = []
    if "crash" in r:
        return {"fail": [f"crash: {r['crash']}"], "warn": []}
    if not r["ledger_valid"]:
        fails.append("replay ledger chain invalid")
    for key, n in r["numeric"].items():
        fails.append(f"{key}: {n} values")
    cons = r["conservation"]
    if cons["element_rel_error"] > CONSERVATION_REL_TOL:
        fails.append(f"element balance error {cons['element_rel_error']:.2e}")
    if cons["water_rel_error"] > CONSERVATION_REL_TOL:
        fails.append(f"water balance error {cons['water_rel_error']:.2e}")
    if cons["lithic_abs_error_kg"] is not None and cons["lithic_abs_error_kg"] > 1e-6:
        fails.append(f"lithic inventory error {cons['lithic_abs_error_kg']:.2e} kg")
    for key, n in r["observer"].items():
        if key.startswith("FAIL_"):
            fails.append(f"{key[5:]}: {n}")
    if r["max_interactions_per_agent_day"] > cap.MAX_INTERACTIONS_PER_TICK:
        fails.append(f"interaction budget exceeded: {r['max_interactions_per_agent_day']} in one agent-day")
    if r.get("max_noop_habit_repeats", 0) >= NOOP_HABIT_LIMIT:
        fails.append(f"superstition loop: one agent repeated a no-op habit {r['max_noop_habit_repeats']} times {r['noop_habits']}")
    elif r["observer"].get("exploited_noops", 0) > 0:
        warns.append(f"no-op chosen as a learned habit {r['observer']['exploited_noops']} times before extinguishing {r['noop_habits']}")
    if r["observer"].get("kills", 0) != r["hunting"]["captures"]:
        fails.append(f"kill count mismatch: observed {r['observer'].get('kills', 0)} vs stats {r['hunting']['captures']}")
    ctx = r["death_context"]
    adult_dehyd_visible = sum(n for k, n in ctx.items() if k.startswith("dehydration|adult|water_visible"))
    if adult_dehyd_visible:
        fails.append(f"water-seeking regression: {adult_dehyd_visible} adult dehydration deaths with water in view")
    adult_dehyd_remembered = sum(n for k, n in ctx.items() if k.startswith("dehydration|adult|water_remembered"))
    if adult_dehyd_remembered:
        warns.append(f"{adult_dehyd_remembered} adult dehydration deaths with water remembered")
    beside_food = ctx.get("energy|adult|food_in_own_cell", 0)
    if beside_food:
        warns.append(f"{beside_food} adults starved with >=5 kg plant/seed in their cell")
    if r["founders"] and r["alive_min"] < 0.5 * r["founders"]:
        warns.append(f"population fell to {r['alive_min']} of {r['founders']} founders")
    apart = r["observer"].get("dependent_days_apart", 0)
    if apart and apart > 0.05 * max(1, r["observer"].get("dependent_days", 0)):
        warns.append(f"dependents apart from caregiver on {apart} of {r['observer']['dependent_days']} dependent-days")
    if r["fatigue_blocked_share"] > 0.25:
        warns.append(f"fatigue above {FATIGUE_BLOCK} on {r['fatigue_blocked_share']:.0%} of agent-days (interactions blocked)")
    n = r["observer"].get("interactions", 0)
    if n and r["observer"].get("noop_interactions", 0) / n > 0.5:
        warns.append(f"no-op share {r['observer']['noop_interactions'] / n:.0%} of interactions")
    return {"fail": fails, "warn": warns}


def unobserved_digest(seed: str, arm: str, days: int) -> str:
    """Ledger digest of the same run with no observer installed."""
    sim = GenesisSimulation(build_config(seed, arm))
    sim.run(days)
    return sim.ledger.digest()
