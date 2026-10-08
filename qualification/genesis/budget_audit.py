"""Caregiver energy budget, injury sources and imitation audit (read-only).

Three diagnostics on production runs. Each wraps production functions only to
look at their inputs and outputs; every wrapper returns exactly what the
original returned, and `--check-digest` confirms the ledger digest is
identical with and without the audit.

1. Energy ledger (adults, per day). Every term that changes an adult's energy
   in a tick, measured where it happens:
     intake        energy credited by eating (forage_at_cell), net of handling
     clamp_loss    food energy offered but not credited (reserve at its cap)
     interactions  effort and anything else inside run_interactions
     nursing       energy drawn from a caregiver by _provision_dependent
     provisioning  handling paid by a caregiver giving solid food (solid-food-v1)
     thermal       _apply_physiology (cold/heat stress)
     catabolism    lean tissue broken down to cover a deficit (reference-v2)
     basal, move   the inline costs, from the agent's effective profile
     birth         energy given to a child born today
   residual = actual change - sum of terms. It must be ~0: the budget closes.
   Also recorded: kg eaten against the gut cap, the share of it eaten beyond
   need (its energy refused by a full reserve), and food in the cell. Milk is
   accounted from the run's nursing_stats (produced, charged, conversion
   heat, absorbed, unabsorbed) when nursing is demand-limited.
   Hand-feeding checks: each check's outcome with the child's reserve against
   the 0.75 trigger, grouped by the caregiver's own reserve.

2. Injury ledger (everyone, per day): injury change by source
     predator      _apply_predator_threat
     ingestion     hazard from eating (forage_at_cell)
     interactions  run_interactions (capture, tools)
     physiology    _apply_physiology, net of healing (exposure, fire, healing)
   An injury death is attributed by the positive contributions over the
   agent's last 60 days. A death with no tracked source stays unattributed.

3. Imitation audit: every imitated try, with what was seen, the conditions,
   what the act produced, its same-day reward terms, and what became of its
   value by the end of the run.

  python -m qualification.genesis.budget_audit --arm v1@reference-v2 --days 730 --json out.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "src", ROOT, ROOT / "experiments" / "genesis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import hrm_genesis.human.biology as biology  # noqa: E402
import hrm_genesis.human.interactions as cap  # noqa: E402
from hrm_genesis import GenesisConfig, GenesisSimulation  # noqa: E402
from hrm_genesis.human.diet import available_kg  # noqa: E402
from qualification.genesis.tier_observer import build_config, unobserved_digest  # noqa: E402

DEFAULT_SEEDS = ("agentus-demography-a", "agentus-demography-b", "agentus-demography-c", "agentus-demography-d")
ENERGY_TERMS = ("intake", "interactions", "nursing", "provisioning", "thermal", "catabolism", "basal", "move", "birth")
INJURY_SOURCES = ("predator", "ingestion", "interactions", "physiology")
ATTRIBUTION_DAYS = 60


class Audit:
    def __init__(self) -> None:
        self.energy: dict[str, Counter] = defaultdict(Counter)
        self.food: dict[str, dict] = {}
        self.injury: dict[str, Counter] = defaultdict(Counter)
        self.profiles: dict[str, dict] = {}
        self.tries: list[dict] = []
        self.feeding_checks: list[tuple] = []
        self._pending: dict[int, dict] = {}
        self._originals: list[tuple[object, str, object]] = []

    def install(self) -> None:
        audit = self
        o_forage = biology.forage_at_cell
        o_provision = biology._provision_dependent
        o_solid = getattr(biology, "_provision_solid_food", None)
        o_physiology = biology._apply_physiology
        o_catabolize = biology._catabolize_lean_tissue
        o_predator = biology._apply_predator_threat
        o_age = biology._age_profile
        o_run = cap.run_interactions
        o_choose = cap.choose
        o_learn = cap.learn_from_tick

        def _age_profile(human, profile):
            out = o_age(human, profile)
            audit.profiles[str(human["id"])] = out
            return out

        def forage_at_cell(human, producer_cell, carcass_cell, profile, *args, **kwargs):
            e0, i0 = float(human["energy"]), float(human.get("injury", 0.0))
            plant_here = available_kg("plant_tissue", producer_cell, carcass_cell)
            records = o_forage(human, producer_cell, carcass_cell, profile, *args, **kwargs)
            hid = str(human["id"])
            credited = float(human["energy"]) - e0
            offered = sum(float(r["kcal"]) - float(r["handling_kcal"]) for r in records)
            audit.energy[hid]["intake"] += credited
            audit.energy[hid]["clamp_loss"] += offered - credited
            audit.injury[hid]["ingestion"] += float(human.get("injury", 0.0)) - i0
            kcal_by_kind = Counter()
            for r in records:
                kcal_by_kind[r["kind"]] += float(r["kcal"]) - float(r["handling_kcal"])
            kg = sum(float(r["kg"]) for r in records)
            # Food eaten whose energy the full reserve could not take: the
            # matching share of the day's mass (removed from the world, unused).
            surplus_kg = kg * (offered - credited) / offered if offered > 0.0 else 0.0
            audit.food[hid] = {"kg": kg, "gut_kg": float(profile["bite_cap_kg"]), "surplus_kg": surplus_kg,
                               "plant_here_kg": plant_here, "kcal_by_kind": dict(kcal_by_kind)}
            return records

        def _provision_dependent(child, caregiver, profile, *args, **kwargs):
            e0 = None if caregiver is None else float(caregiver["energy"])
            c0 = float(child["energy"])
            out = o_provision(child, caregiver, profile, *args, **kwargs)
            if caregiver is not None:
                audit.energy[str(caregiver["id"])]["nursing"] += float(caregiver["energy"]) - e0
                # What the child actually gained from milk (it is capped by the
                # child's store); compare with what the mother paid.
                audit.energy[str(caregiver["id"])]["milk_to_child"] += float(child["energy"]) - c0
            return out

        def _provision_solid_food(child, caregiver, child_profile, caregiver_profile, pcell, ccell, eaten_kg, stats):
            e0 = None if caregiver is None else float(caregiver["energy"])
            c0 = float(child["energy"])
            before = dict(stats.get("solid_food_outcomes", {}))
            out = o_solid(child, caregiver, child_profile, caregiver_profile, pcell, ccell, eaten_kg, stats)
            after = stats.get("solid_food_outcomes", {})
            outcome = next((k for k in after if int(after[k]) > int(before.get(k, 0))), None)
            if outcome is not None:
                # One hand-feeding check: its outcome, the child's reserve
                # against the trigger (same reference as the production check),
                # and the caregiver's own reserve at that moment.
                ref = float(child_profile.get("satiety_reference_kcal", child_profile.get("energy_capacity_kcal", 1.0)))
                ref *= max(0.10, float(child_profile.get("development_scale", 1.0)))
                cref = None if caregiver is None else float(caregiver_profile.get(
                    "satiety_reference_kcal", caregiver_profile.get("energy_capacity_kcal", 1.0)))
                audit.feeding_checks.append((
                    outcome, int(child.get("age_ticks", 0)), c0 / max(1e-9, ref),
                    None if caregiver is None else e0 / max(1e-9, cref),
                ))
            if caregiver is not None:
                audit.energy[str(caregiver["id"])]["provisioning"] += float(caregiver["energy"]) - e0
                audit.energy[str(caregiver["id"])]["solid_to_child_kcal"] += float(child["energy"]) - c0
                audit.energy[str(caregiver["id"])]["solid_to_child_kg"] += float(out)
            return out

        def _apply_physiology(human, *args, **kwargs):
            e0, i0 = float(human["energy"]), float(human.get("injury", 0.0))
            out = o_physiology(human, *args, **kwargs)
            hid = str(human["id"])
            audit.energy[hid]["thermal"] += float(human["energy"]) - e0
            audit.injury[hid]["physiology"] += float(human.get("injury", 0.0)) - i0
            return out

        def _catabolize_lean_tissue(human, profile, detritus):
            e0 = float(human["energy"])
            out = o_catabolize(human, profile, detritus)
            audit.energy[str(human["id"])]["catabolism"] += float(human["energy"]) - e0
            return out

        def _apply_predator_threat(human, consumer_state, epoch=None):
            i0 = float(human.get("injury", 0.0))
            n = o_predator(human, consumer_state, epoch)
            hid = str(human["id"])
            audit.injury[hid]["predator"] += float(human.get("injury", 0.0)) - i0
            audit.injury[hid]["predator_attacks"] += n
            return n

        def run_interactions(humans, human, *args, **kwargs):
            e0, i0 = float(human["energy"]), float(human.get("injury", 0.0))
            ctx = o_run(humans, human, *args, **kwargs)
            hid = str(human["id"])
            audit.energy[hid]["interactions"] += float(human["energy"]) - e0
            audit.injury[hid]["interactions"] += float(human.get("injury", 0.0)) - i0
            return ctx

        def choose(ctx, options, step, hungry):
            tries_before = sum(ctx.stats.get("imitation_tries", {}).values())
            picked = o_choose(ctx, options, step, hungry)
            # An imitation pick is exactly a step that raised the production
            # counter; the same untried act can be imitated on two steps of a day.
            if picked is not None and sum(ctx.stats.get("imitation_tries", {}).values()) > tries_before:
                key = picked[0]
                h = ctx.human
                seen = [dict(e) for e in h["cognition"].get("witnessed", []) if e.get("act") == key]
                audit._pending.setdefault(id(ctx), []).append({
                    "agent": ctx.agent_id, "epoch": int(ctx.epoch), "key": key, "step": int(step),
                    "seen_from": list(ctx.imitated.get(key, [])),
                    "seen_events": [{"actor": e["actor"], "epoch": e["epoch"],
                                     "salience": cap.witnessed_salience(e),
                                     "appeared": e.get("appeared", []), "transformed": e.get("transformed"),
                                     "killed": e.get("killed"), "exposed_kg": e.get("exposed_kg"),
                                     "eaten_kg": e.get("eaten_kg"), "hurt": e.get("hurt")} for e in seen],
                    "hungry": bool(hungry), "energy": round(float(h["energy"]), 1),
                    "fatigue": round(float(h.get("fatigue", 0.0)), 3),
                    "age_years": round(int(h["age_ticks"]) / 365.0, 1),
                    "options_offered": len(options),
                    "animals_here": len([a for a in ctx.consumers.get("animals", [])
                                         if (int(a["x"]), int(a["y"])) == ctx.xy]),
                    "held_objects": len(ctx.held()),
                })
            return picked

        def learn_from_tick(ctx, intake):
            pending = audit._pending.pop(id(ctx), [])
            values_before = dict(ctx.human["cognition"].get("affordance_values", {}))
            out = o_learn(ctx, intake)
            if pending:
                values = ctx.human["cognition"].get("affordance_values", {})
                basal = float(ctx.profile["basal_energy_kcal_per_tick"])
                used: Counter = Counter()
                for row in pending:
                    key = row["key"]
                    performed = [o for k, o in ctx.performed if k == key]
                    o = performed[used[key]] if used[key] < len(performed) else {}
                    used[key] += 1
                    effort = float(o.get("effort_kcal", 0.0))
                    injury = float(o.get("injury", 0.0))
                    row.update({
                        "performed": bool(o),
                        "same_day_repeat": used[key] > 1,
                        "effort_kcal": round(effort, 2),
                        "injury": round(injury, 4),
                        "capture": bool(o.get("capture")),
                        "access_bonus_kg": round(float(o.get("access_bonus_kg", 0.0)), 4),
                        "exposed_kg": round(float(o.get("exposed_kg", 0.0)), 4),
                        "created_classes": o.get("created_classes"),
                        "appeared_classes": o.get("appeared_classes"),
                        "ate_kg_by_kind": {r["kind"]: round(float(r["kg"]), 4) for r in intake if float(r["kg"]) > 0.0},
                        "value_before": values_before.get(key, {}).get("v"),
                        "value_after_day": values.get(key, {}).get("v"),
                        "reward_effort_term": round(-effort / basal, 5),
                        "reward_injury_term": round(-2.0 * injury, 5),
                    })
                    # With no gain the reward is exactly the effort and injury terms.
                    row["reward_is_cost_only"] = not o.get("capture") and float(o.get("access_bonus_kg", 0.0)) <= 0.0
                    audit.tries.append(row)
            return out

        for module, name, fn in (
            (biology, "forage_at_cell", forage_at_cell), (biology, "_provision_dependent", _provision_dependent),
            *([(biology, "_provision_solid_food", _provision_solid_food)] if o_solid is not None else []),
            (biology, "_apply_physiology", _apply_physiology), (biology, "_catabolize_lean_tissue", _catabolize_lean_tissue),
            (biology, "_apply_predator_threat", _apply_predator_threat), (biology, "_age_profile", _age_profile),
            (cap, "run_interactions", run_interactions), (cap, "choose", choose), (cap, "learn_from_tick", learn_from_tick),
        ):
            self._originals.append((module, name, getattr(module, name)))
            setattr(module, name, fn)

    def uninstall(self) -> None:
        for module, name, fn in reversed(self._originals):
            setattr(module, name, fn)
        self._originals.clear()

    def new_day(self) -> None:
        self.energy = defaultdict(Counter)
        self.food = {}
        self.injury = defaultdict(Counter)
        self.profiles = {}


def run_audit(seed: str, arm: str, days: int, consumer_timebase: str | None = None) -> dict:
    started = time.perf_counter()
    audit = Audit()
    audit.install()
    try:
        config = build_config(seed, arm)
        if consumer_timebase:
            config = GenesisConfig(**{**config.__dict__, "consumer_timebase": consumer_timebase})
        sim = GenesisSimulation(config)
        profile = sim.human_state()["physiology_profile"]
        maturity = int(profile["maturity_ticks"])
        independent = int(profile["independent_feeding_age_ticks"])
        satiety = float(profile.get("satiety_reference_kcal", profile["energy_capacity_kcal"]))
        rows: list[dict] = []
        injury_history: dict[str, list[Counter]] = defaultdict(list)
        injury_deaths: list[dict] = []
        attacks_by_year: Counter = Counter()
        max_residual = 0.0
        for day in range(days):
            before = {str(p["id"]): p for p in sim.human_state()["humans"]}
            dependents = Counter(str(p.get("caregiver_id")) for p in before.values()
                                 if int(p["age_ticks"]) < independent and p.get("caregiver_id"))
            audit.new_day()
            sim.run(1)
            after_state = sim.human_state()
            after = {str(p["id"]): p for p in after_state["humans"]}
            births = Counter(str(p.get("caregiver_id")) for pid, p in after.items() if pid not in before)
            birth_energy = defaultdict(float)
            for pid, p in after.items():
                if pid not in before:
                    birth_energy[str(p.get("caregiver_id"))] += float(p["energy"])
            for pid, src in audit.injury.items():
                injury_history[pid].append(src)
                attacks_by_year[day // 365 + 1] += int(src.get("predator_attacks", 0))
            for rec in after_state.get("death_records", []):
                if rec["epoch"] == day and rec["cause"] == "injury":
                    window = injury_history.get(rec["id"], [])[-ATTRIBUTION_DAYS:]
                    gains = Counter()
                    for c in window:
                        for s in INJURY_SOURCES:
                            if float(c.get(s, 0.0)) > 0.0:
                                gains[s] += float(c[s])
                    total = sum(gains.values())
                    injury_deaths.append({
                        "id": rec["id"], "day": day,
                        "adult": int(before[rec["id"]]["age_ticks"]) >= maturity if rec["id"] in before else None,
                        "injury_gain_by_source": {s: round(v, 3) for s, v in gains.items()},
                        "attacks": sum(int(c.get("predator_attacks", 0)) for c in window),
                        "attributed_to": (max(gains, key=gains.get) if total > 0 else "unattributed"),
                        "share": round(max(gains.values()) / total, 2) if total > 0 else 0.0,
                    })
            for pid, p0 in before.items():
                p1 = after.get(pid)
                if p1 is None or int(p0["age_ticks"]) < maturity:
                    continue
                eff = audit.profiles.get(pid, {})
                terms = dict(audit.energy.get(pid, Counter()))
                moved = (int(p0["x"]), int(p0["y"])) != (int(p1["x"]), int(p1["y"]))
                terms["basal"] = -float(eff.get("basal_energy_kcal_per_tick", 0.0))
                terms["move"] = -float(eff.get("move_energy_kcal_per_tick", 0.0)) if moved else 0.0
                terms["birth"] = -birth_energy.get(pid, 0.0)
                change = float(p1["energy"]) - float(p0["energy"])
                residual = change - sum(float(terms.get(t, 0.0)) for t in ENERGY_TERMS)
                max_residual = max(max_residual, abs(residual))
                food = audit.food.get(pid, {})
                rows.append({
                    "day": day, "id": pid, "caring": dependents.get(pid, 0) > 0, "dependents": dependents.get(pid, 0),
                    "reserve": float(p0["energy"]) / satiety, "energy": float(p0["energy"]),
                    "change": change, "residual": residual,
                    **{t: float(terms.get(t, 0.0)) for t in ENERGY_TERMS}, "clamp_loss": float(terms.get("clamp_loss", 0.0)),
                    "milk_to_child": float(terms.get("milk_to_child", 0.0)),
                    "solid_to_child_kcal": float(terms.get("solid_to_child_kcal", 0.0)),
                    "solid_to_child_kg": float(terms.get("solid_to_child_kg", 0.0)),
                    "kg": food.get("kg", 0.0), "surplus_kg": food.get("surplus_kg", 0.0), "gut_kg": food.get("gut_kg", 0.0), "plant_here_kg": food.get("plant_here_kg", 0.0),
                    "kcal_by_kind": food.get("kcal_by_kind", {}),
                    "born_today": births.get(pid, 0),
                })
        final = sim.human_state()
        for t in audit.tries:
            living = next((p for p in final["humans"] if str(p["id"]) == t["agent"]), None)
            entry = (living or {}).get("cognition", {}).get("affordance_values", {}).get(t["key"])
            t["end_of_run"] = {"alive": living is not None, "value": None if entry is None else entry.get("v"),
                               "uses": None if entry is None else entry.get("n"),
                               "exploited_by_this_agent": t["agent"] in final.get("capacity_stats", {}).get("exploit_agents", {}).get(t["key"], [])}
        result = {"seed": seed, "arm": arm, "consumer_timebase": config.consumer_timebase, "days": days, "ledger_digest": sim.ledger.digest(),
                  "ledger_valid": sim.ledger.verify_chain(), "max_energy_residual_kcal": max_residual,
                  "profile": {k: profile.get(k) for k in ("bite_cap_kg", "food_energy_kcal_per_kg", "assimilation",
                                                          "basal_energy_kcal_per_tick", "nursing_energy_kcal_per_tick",
                                                          "lactation_efficiency", "energy_capacity_kcal",
                                                          "satiety_reference_kcal", "move_energy_kcal_per_tick")},
                  "rows": rows, "injury_deaths": injury_deaths, "predator_attacks_by_year": dict(attacks_by_year),
                  "deaths_by_cause": {k: v for k, v in final.get("cumulative_deaths_by_cause", {}).items() if v},
                  "imitation_tries": audit.tries,
                  "feeding_checks": summarize_feeding(audit.feeding_checks),
                  "nursing_model": config.nursing_model,
                  "nursing_stats": final.get("nursing_stats", {})}
    except Exception as exc:
        import traceback
        result = {"seed": seed, "arm": arm, "days": days, "crash": f"{type(exc).__name__}: {exc}",
                  "traceback": traceback.format_exc(limit=8)}
    finally:
        audit.uninstall()
    result["seconds"] = round(time.perf_counter() - started, 1)
    return result


def _job(args):
    return run_audit(*args)


def summarize_feeding(checks: list[tuple]) -> dict:
    """Hand-feeding outcomes, overall and by the caregiver's reserve band.

    Tests one hypothesis: milk keeps children above the feeding trigger (child
    reserve >= 0.75) even while caregivers run down their own reserves.
    """
    def band(r):
        return "no caregiver" if r is None else ("< 0.25" if r < 0.25 else ("< 0.75" if r < 0.75 else ">= 0.75"))
    out = {"checks": len(checks), "outcomes": dict(Counter(c[0] for c in checks).most_common())}
    by_band = {}
    for c in checks:
        b = by_band.setdefault(band(c[3]), {"checks": 0, "outcomes": Counter(), "child_reserve": []})
        b["checks"] += 1
        b["outcomes"][c[0]] += 1
        if c[0] != "too_young":
            b["child_reserve"].append(c[2])
    for b in by_band.values():
        rs = sorted(b.pop("child_reserve"))
        b["outcomes"] = dict(b["outcomes"].most_common())
        b["past_onset_child_reserve"] = ({"n": len(rs), "min": round(rs[0], 3), "median": round(rs[len(rs) // 2], 3),
                                          "share_at_or_above_trigger": round(sum(1 for r in rs if r >= 0.75) / len(rs), 3)}
                                         if rs else {"n": 0})
    out["by_caregiver_reserve"] = dict(sorted(by_band.items()))
    return out


def summarize_energy(rows: list[dict]) -> dict:
    groups = {
        "non-caregiver adults": [r for r in rows if not r["caring"]],
        "caregivers": [r for r in rows if r["caring"]],
        "caregivers, reserve < 0.75": [r for r in rows if r["caring"] and r["reserve"] < 0.75],
        "caregivers, reserve < 0.25": [r for r in rows if r["caring"] and r["reserve"] < 0.25],
        "caregivers, losing energy": [r for r in rows if r["caring"] and r["change"] < 0.0],
    }
    out = {}
    for name, rs in groups.items():
        n = len(rs)
        if not n:
            out[name] = {"days": 0}
            continue
        mean = lambda k: sum(float(r[k]) for r in rs) / n  # noqa: E731
        out[name] = {
            "days": n,
            "mean_kcal_per_day": {k: round(mean(k), 1) for k in ENERGY_TERMS + ("clamp_loss", "change")},
            "milk_paid_vs_absorbed_kcal": (round(-mean("nursing"), 1), round(mean("milk_to_child"), 1)),
            "solid_food_to_children": (round(mean("solid_to_child_kg"), 4), round(mean("solid_to_child_kcal"), 1)),
            "eaten_vs_beyond_need_kg": (round(mean("kg"), 3), round(mean("surplus_kg"), 3)),
            "gut_fill_mean": round(sum(r["kg"] / r["gut_kg"] for r in rs if r["gut_kg"] > 0) / n, 3),
            "gut_full_days": round(sum(1 for r in rs if r["gut_kg"] > 0 and r["kg"] >= 0.99 * r["gut_kg"]) / n, 3),
            "food_in_cell_ge_gut_days": round(sum(1 for r in rs if r["plant_here_kg"] >= r["gut_kg"] > 0) / n, 3),
            "mean_reserve": round(mean("reserve"), 3),
            "dependents": dict(sorted(Counter(int(r["dependents"]) for r in rs).items())),
            "nursing_per_dependent_kcal": round(sum(float(r["nursing"]) for r in rs) / max(1, sum(int(r["dependents"]) for r in rs)), 1),
            "offered_kcal_by_kind": {k: round(v / n, 1) for k, v in sorted(
                sum((Counter(r["kcal_by_kind"]) for r in rs), Counter()).items())},
        }
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="budget_audit")
    p.add_argument("--seeds", nargs="*", default=list(DEFAULT_SEEDS))
    p.add_argument("--arm", default="v1@reference-v2")
    p.add_argument("--days", type=int, default=730)
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--json")
    p.add_argument("--check-digest", action="store_true")
    p.add_argument("--consumer-timebase", choices=("elapsed-time-v2", "elapsed-time-v1", "per-tick-legacy"),
                   help="override the consumer timebase (per-tick-legacy reproduces pre-D2 runs)")
    a = p.parse_args(argv)
    t = time.perf_counter()
    jobs = [(s, a.arm, a.days, a.consumer_timebase) for s in a.seeds]
    if a.parallel <= 1 or len(jobs) == 1:
        results = [_job(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=min(a.parallel, len(jobs))) as pool:
            results = list(pool.map(_job, jobs))
    status = 0
    ok = [r for r in results if "crash" not in r]
    for r in results:
        if "crash" in r:
            print(f"CRASH {r['seed']}: {r['crash']}\n{r['traceback']}")
            status = 1
            continue
        print(f"{r['seed']} {r['arm']}: deaths {r['deaths_by_cause']}  max |energy residual| {r['max_energy_residual_kcal']:.2e} kcal  "
              f"predator attacks by year {r['predator_attacks_by_year']}  {r['seconds']}s")
    rows = [row for r in ok for row in r["rows"]]
    summary = summarize_energy(rows)
    print(f"\n== ENERGY LEDGER ({a.arm}; adults; mean kcal per agent-day) ==")
    if ok:
        print(f"profile: {ok[0]['profile']}")
    for name, s in summary.items():
        print(f"\n{name}: {s.get('days', 0)} days")
        if s.get("days"):
            print(f"  {s['mean_kcal_per_day']}")
            print(f"  gut fill {s['gut_fill_mean']}  gut full on {s['gut_full_days']:.0%} of days  "
                  f"food in own cell >= gut on {s['food_in_cell_ge_gut_days']:.0%}  mean reserve {s['mean_reserve']}")
            print(f"  kg eaten / of which beyond need (energy not taken up, reserve full) per day {s['eaten_vs_beyond_need_kg']}")
            print(f"  milk paid / absorbed by children (kcal/day) {s['milk_paid_vs_absorbed_kcal']}  "
                  f"solid food to children (kg, kcal per day) {s['solid_food_to_children']}")
            print(f"  dependents per day {s['dependents']}  nursing per dependent {s['nursing_per_dependent_kcal']} kcal  "
                  f"food offered by kind (kcal/day, before any clamp) {s['offered_kcal_by_kind']}")
    print("\n== MILK (whole run, all caregivers) ==")
    for r in ok:
        n = r.get("nursing_stats") or {}
        if not n:
            print(f"  {r['seed']}: {r.get('nursing_model')} (no milk accounting recorded)")
            continue
        days = max(1, int(n.get("nursing_days", 0)))
        per = {k.removesuffix("_kcal"): round(float(v) / days, 1) for k, v in n.items() if k.endswith("_kcal")}
        print(f"  {r['seed']}: {r['nursing_model']}  nursing days {n.get('nursing_days', 0)}  "
              f"demand-limited on {int(n.get('nursing_days_demand_limited', 0)) / days:.0%}  kcal per nursing day {per}")
    print("\n== HAND-FEEDING CHECKS (outcome; child reserve vs trigger 0.75, by caregiver reserve) ==")
    for r in ok:
        f = r.get("feeding_checks") or {}
        print(f"  {r['seed']}: {f.get('checks', 0)} checks  {f.get('outcomes', {})}")
        for b, row in (f.get("by_caregiver_reserve") or {}).items():
            print(f"    caregiver reserve {b}: {row['checks']} checks {row['outcomes']}  past onset: {row['past_onset_child_reserve']}")
    print("\n== INJURY DEATHS ==")
    for r in ok:
        for d in r["injury_deaths"]:
            print(f"  {r['seed']} day {d['day']} {d['id']} adult={d['adult']}: {d['attributed_to']} ({d['share']:.0%})  "
                  f"gains {d['injury_gain_by_source']}  attacks in last {ATTRIBUTION_DAYS} days {d['attacks']}")
    print("\n== IMITATED TRIES ==")
    for r in ok:
        for tr in r["imitation_tries"]:
            print(f"  {r['seed']} day {tr['epoch']} {tr['agent']} {tr['key']}: seen {len(tr['seen_events'])}x from {tr['seen_from']} "
                  f"(salience {[e['salience'] for e in tr['seen_events']]})  hungry={tr['hungry']}  "
                  f"effort {tr.get('effort_kcal')} kcal  injury {tr.get('injury')}  capture {tr.get('capture')}  "
                  f"access bonus {tr.get('access_bonus_kg')}  ate {tr.get('ate_kg_by_kind')}  "
                  f"value after day {tr.get('value_after_day')}{' (repeat same day)' if tr.get('same_day_repeat') else ''}  end {tr['end_of_run']}")
    if a.check_digest:
        for r in ok:
            if a.consumer_timebase:
                print(f"digest check skipped for {r['seed']}: timebase override")
                continue
            same = unobserved_digest(r["seed"], r["arm"], r["days"]) == r["ledger_digest"]
            print(f"audit non-causal ({r['seed']}): {'IDENTICAL' if same else 'DIFFERENT'} ledger digest")
            status = status or (0 if same else 1)
    if a.json:
        slim = [{k: v for k, v in r.items() if k != "rows"} for r in results]
        Path(a.json).write_text(json.dumps({"results": slim, "energy_summary": summary}, indent=1, default=str))
    print(f"\nbudget audit wall time {time.perf_counter() - t:.0f}s  RESULT: {'FAIL' if status else 'PASS'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
