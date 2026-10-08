"""Read-only food intake and seasonal shortage diagnosis for Homo agentus.

Runs the same four-seed, 730-day configuration as
``run_agentus_demography_multiseed.py`` with no resource, physiology, or
behavior changes. Internal biology/ecology functions are wrapped only to
record what they already compute; wrappers return the original results
unchanged. Every number here is an observer measurement and is never
supplied to agents.

Outputs one JSON document (``--out``) with per-seed daily ecology series,
per-life-stage energy budgets, intake limitation counts, seasonal summaries,
and pre-death windows.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import replace
from multiprocessing import Pool

import hrm_genesis.runner as runner_module
from hrm_genesis import GenesisConfig, GenesisSimulation
from hrm_genesis.ecology import plants as plants_module
from hrm_genesis.human import biology as biology_module


SEEDS = [
    "agentus-demography-a",
    "agentus-demography-b",
    "agentus-demography-c",
    "agentus-demography-d",
]
DAYS = 730
PRE_DEATH_WINDOW = 30
SEASON_DAYS = 365 / 4.0


def _config(seed: str) -> GenesisConfig:
    return GenesisConfig(
        master_seed=seed,
        world_width=16,
        world_height=16,
        ticks_per_year=365,
        producer_ecology_enabled=True,
        consumer_ecology_enabled=True,
        human_biology_enabled=True,
        human_cognition_enabled=True,
        human_actions_enabled=True,
        multi_population_enabled=True,
        material_scale_factor=1000.0,
        human_calibration_enabled=True,
    )


def _mass(elements: dict) -> float:
    return sum(float(v) for v in elements.values())


def _edible(state: dict) -> float:
    return sum(_mass(c["plant_elements_kg"]) for c in state["cells"])


def _stocks(producer_state: dict, matter_state: dict) -> dict:
    """Ecosystem pools after the producer step (observer measurement)."""
    totals = {"woody_kg": 0.0, "seed_kg": 0.0, "detritus_kg": 0.0}
    for cell in producer_state["cells"]:
        totals["woody_kg"] += _mass(cell.get("woody_elements_kg", {}))
        totals["seed_kg"] += _mass(cell["seed_elements_kg"])
        totals["detritus_kg"] += _mass(cell["detritus_elements_kg"])
    totals["soil_water_kg"] = sum(float(c["soil_water_kg"]) for c in matter_state["cells"])
    for symbol in ("N", "P", "K"):
        totals[f"matter_{symbol}_kg"] = sum(float(c["elements_kg"].get(symbol, 0.0)) for c in matter_state["cells"])
    return {k: round(v, 4) for k, v in totals.items()}


def _stage(human: dict, profile: dict) -> str:
    adjusted = biology_module._age_profile(human, profile)
    dependence = float(adjusted.get("caregiver_dependence", 0.0))
    if dependence >= 1.0:
        return "dependent"
    if dependence > 0.0:
        return "weaning"
    if int(human["age_ticks"]) < int(profile["maturity_ticks"]):
        return "juvenile"
    return "adult"


class Recorder:
    """Collects one tick of measurements from wrapped pure functions."""

    def __init__(self) -> None:
        self.tick: dict = {}
        self.calls = 0

    def reset(self, epoch: int) -> None:
        self.calls += 1
        self.tick = {
            "epoch": epoch,
            "eat": {},
            "physiology": {},
            "nursing_out": defaultdict(float),
            "nursing_in": {},
            "effort": {},
            "gross_growth_kg": 0.0,
        }


@contextmanager
def instrumented(recorder: Recorder):
    originals = {
        "eat": biology_module._eat,
        "physiology": biology_module._apply_physiology,
        "provision": biology_module._provision_dependent,
        "sequence": biology_module.execute_live_sequence,
        "growth": plants_module._growth_limit,
        "producers": runner_module.evolve_producers,
        "consumers": runner_module.evolve_consumers,
        "humans": runner_module.evolve_humans,
    }

    def eat(human, pcell, profile):
        available = _mass(pcell["plant_elements_kg"])
        energy_before = float(human["energy"])
        dry_before = _mass(human["body_elements_kg"])
        consumed = originals["eat"](human, pcell, profile)
        potential = consumed * float(profile["food_energy_kcal_per_kg"]) * float(profile["assimilation"])
        recorder.tick["eat"][str(human["id"])] = {
            "available_kg": available,
            "bite_cap_kg": float(profile["bite_cap_kg"]),
            "consumed_kg": consumed,
            "potential_kcal": potential,
            "credited_kcal": float(human["energy"]) - energy_before,
            "energy_before_eat": energy_before,
            "energy_capacity_kcal": float(profile.get("energy_capacity_kcal", math.inf)),
            "dry_retained_kg": _mass(human["body_elements_kg"]) - dry_before,
        }
        return consumed

    def physiology(human, world_cell, moved, profile=None, producer_cell=None, **kwargs):
        energy_before = float(human["energy"])
        originals["physiology"](human, world_cell, moved, profile, producer_cell, **kwargs)
        dependence = float((profile or {}).get("caregiver_dependence", 0.0))
        move_cost = 0.0
        if moved:
            move_cost = float(profile["move_energy_kcal_per_tick"]) * (0.25 if dependence > 0.0 else 1.0)
        recorder.tick["physiology"][str(human["id"])] = {
            "moved": bool(moved),
            "move_kcal": move_cost,
            "thermal_kcal": energy_before - float(human["energy"]),
            "basal_kcal": float(profile["basal_energy_kcal_per_tick"]),
            "temperature_c": float(world_cell["temperature"]),
            "xy": [int(human["x"]), int(human["y"])],
        }

    def provision(child, caregiver, profile, *args, **kwargs):
        caregiver_energy = float(caregiver["energy"]) if caregiver is not None else 0.0
        child_energy = float(child["energy"])
        result = originals["provision"](child, caregiver, profile, *args, **kwargs)
        if caregiver is not None:
            recorder.tick["nursing_out"][str(caregiver["id"])] += caregiver_energy - float(caregiver["energy"])
        recorder.tick["nursing_in"][str(child["id"])] = float(child["energy"]) - child_energy
        return result

    def sequence(sequence_, human, pcell):
        updated_human, updated_cell, trace = originals["sequence"](sequence_, human, pcell)
        recorder.tick["effort"][str(human["id"])] = float(trace.get("effort_energy_kcal", 0.0))
        return updated_human, updated_cell, trace

    def growth(matter_cell, desired_growth):
        allowed = originals["growth"](matter_cell, desired_growth)
        recorder.tick["gross_growth_kg"] += allowed
        recorder.tick["desired_growth_kg"] = recorder.tick.get("desired_growth_kg", 0.0) + max(0.0, desired_growth)
        if allowed + 1e-12 < desired_growth:
            limits = {
                symbol: max(0.0, float(matter_cell["elements_kg"].get(symbol, 0.0))) / fraction
                for symbol, fraction in plants_module.PLANT_ELEMENT_FRACTIONS.items()
            }
            limits["water"] = max(0.0, float(matter_cell["soil_water_kg"])) / plants_module.WATER_KG_PER_KG_GROWTH
            limiter = min(limits, key=limits.get)
            counts = recorder.tick.setdefault("growth_limited_cells", {})
            counts[limiter] = counts.get(limiter, 0) + 1
        return allowed

    def producers(producer_state, matter_state, world_state, epoch):
        recorder.tick["edible_start_kg"] = _edible(producer_state)
        result = originals["producers"](producer_state, matter_state, world_state, epoch)
        recorder.tick["edible_after_plants_kg"] = _edible(result[0])
        recorder.tick["stocks"] = _stocks(result[0], result[1])
        return result

    def consumers(consumer_state, producer_state, matter_state, world_state, epoch):
        result = originals["consumers"](consumer_state, producer_state, matter_state, world_state, epoch)
        recorder.tick["edible_after_animals_kg"] = _edible(result[1])
        return result

    def humans(human_state, producer_state, matter_state, world_state, epoch, **kwargs):
        # Producer/consumer wrappers run first in the same callback; keep their values.
        keep = {k: recorder.tick.get(k) for k in ("edible_start_kg", "edible_after_plants_kg", "edible_after_animals_kg", "gross_growth_kg", "desired_growth_kg", "growth_limited_cells", "stocks")}
        recorder.reset(epoch)
        recorder.tick.update(keep)
        recorder.tick["pre_humans_producers"] = producer_state
        recorder.tick["world"] = world_state
        result = originals["humans"](human_state, producer_state, matter_state, world_state, epoch, **kwargs)
        recorder.tick["edible_end_kg"] = _edible(result[1])
        return result

    def reset_growth_before_producers(producer_state, matter_state, world_state, epoch):
        recorder.tick = {"gross_growth_kg": 0.0}
        return producers(producer_state, matter_state, world_state, epoch)

    biology_module._eat = eat
    biology_module._apply_physiology = physiology
    biology_module._provision_dependent = provision
    biology_module.execute_live_sequence = sequence
    plants_module._growth_limit = growth
    runner_module.evolve_producers = reset_growth_before_producers
    runner_module.evolve_consumers = consumers
    runner_module.evolve_humans = humans
    try:
        yield
    finally:
        biology_module._eat = originals["eat"]
        biology_module._apply_physiology = originals["physiology"]
        biology_module._provision_dependent = originals["provision"]
        biology_module.execute_live_sequence = originals["sequence"]
        plants_module._growth_limit = originals["growth"]
        runner_module.evolve_producers = originals["producers"]
        runner_module.evolve_consumers = originals["consumers"]
        runner_module.evolve_humans = originals["humans"]


def _budget_bucket() -> dict:
    return defaultdict(float)


def run_seed(seed: str, days: int = DAYS) -> dict:
    recorder = Recorder()
    with instrumented(recorder):
        sim = GenesisSimulation(_config(seed))
        profile = sim.human_state()["physiology_profile"]
        adult_need_kg = float(profile["basal_energy_kcal_per_tick"]) / (
            float(profile["food_energy_kcal_per_kg"]) * float(profile["assimilation"])
        )
        daily = []
        budgets = defaultdict(_budget_bucket)
        seasonal = defaultdict(_budget_bucket)
        history: dict[str, list[dict]] = defaultdict(list)
        deaths = []
        lives: dict[str, dict] = {}

        for day in range(days):
            before = sim.human_state()
            sim.run(1)
            after = sim.human_state()
            tick = recorder.tick
            if tick.get("epoch") is None:
                raise RuntimeError("human biology callback did not run")
            pcells = {(int(c["x"]), int(c["y"])): c for c in tick["pre_humans_producers"]["cells"]}
            edible = {xy: _mass(c["plant_elements_kg"]) for xy, c in pcells.items()}
            viable = [xy for xy, kg in edible.items() if kg >= adult_need_kg]
            season = int((day % 365) // SEASON_DAYS)
            year = day // 365
            live_ids = {str(p["id"]) for p in after["humans"]}

            intake_kg = 0.0
            for person in before["humans"]:
                pid = str(person["id"])
                stage = _stage(person, profile)
                eat = tick["eat"].get(pid)
                phys = tick["physiology"].get(pid, {})
                nursing_out = tick["nursing_out"].get(pid, 0.0)
                nursing_in = tick["nursing_in"].get(pid, 0.0)
                effort = tick["effort"].get(pid, 0.0)
                credited = eat["credited_kcal"] if eat else 0.0
                potential = eat["potential_kcal"] if eat else 0.0
                consumed = eat["consumed_kg"] if eat else 0.0
                intake_kg += consumed
                ox, oy = int(person["x"]), int(person["y"])
                visible = max(edible[(cx, cy)] for (cx, cy) in edible if abs(cx - ox) + abs(cy - oy) <= 1)
                reach3 = max(edible[(cx, cy)] for (cx, cy) in edible if abs(cx - ox) + abs(cy - oy) <= 3)
                nearest = min((abs(cx - ox) + abs(cy - oy) for cx, cy in viable), default=None)

                if eat is None:
                    limit = "not_feeding"
                elif eat["available_kg"] <= 0.0:
                    limit = "no_food_on_cell"
                elif consumed + 1e-12 >= eat["bite_cap_kg"]:
                    limit = "bite_cap"
                else:
                    limit = "cell_supply"
                saturated = bool(eat) and potential - credited > 1e-6

                b = budgets[stage]
                b["person_days"] += 1
                b["intake_kg"] += consumed
                b["potential_kcal"] += potential
                b["credited_kcal"] += credited
                b["saturation_waste_kcal"] += potential - credited
                b["basal_kcal"] += phys.get("basal_kcal", 0.0)
                b["move_kcal"] += phys.get("move_kcal", 0.0)
                b["thermal_kcal"] += phys.get("thermal_kcal", 0.0)
                b["effort_kcal"] += effort
                b["nursing_out_kcal"] += nursing_out
                b["nursing_in_kcal"] += nursing_in
                b["moved_days"] += 1 if phys.get("moved") else 0
                b[f"limit_{limit}"] += 1
                b["saturated_days"] += 1 if saturated else 0
                b["visible_viable_food_days"] += 1 if visible >= adult_need_kg else 0
                if pid in live_ids:
                    end_energy = float(next(p for p in after["humans"] if str(p["id"]) == pid)["energy"])
                    b["energy_change_kcal"] += end_energy - float(person["energy"])
                    b["energy_change_days"] += 1

                if stage == "adult":
                    s = seasonal[(year, season)]
                    s["adult_days"] += 1
                    s["intake_kcal"] += credited
                    s["potential_kcal"] += potential
                    s["basal_kcal"] += phys.get("basal_kcal", 0.0)
                    s["move_kcal"] += phys.get("move_kcal", 0.0)
                    s["thermal_kcal"] += phys.get("thermal_kcal", 0.0)
                    s["nursing_out_kcal"] += nursing_out
                    s["zero_intake_days"] += 1 if consumed <= 0.0 else 0
                    s["bite_cap_days"] += 1 if limit == "bite_cap" else 0
                    s["visible_viable_days"] += 1 if visible >= adult_need_kg else 0

                net = credited + nursing_in - phys.get("basal_kcal", 0.0) - phys.get("move_kcal", 0.0) - phys.get("thermal_kcal", 0.0) - effort - nursing_out
                history[pid].append({
                    "day": day,
                    "stage": stage,
                    "energy": round(float(person["energy"]), 3),
                    "consumed_kg": round(consumed, 5),
                    "credited_kcal": round(credited, 3),
                    "net_kcal": round(net, 3),
                    "limit": limit,
                    "visible_max_kg": round(visible, 5),
                    "reach3_max_kg": round(reach3, 5),
                    "nearest_viable_steps": nearest,
                    "temperature_c": round(phys.get("temperature_c", float("nan")), 2),
                })
                history[pid] = history[pid][-PRE_DEATH_WINDOW:]
                life = lives.setdefault(pid, {
                    "id": pid,
                    "generation": int(person.get("generation", 0)),
                    "sex": person["sex"],
                    "population_id": person.get("population_id"),
                    "first_day": day,
                })
                life["last_day"] = day

            for record in after.get("death_records", []):
                if str(record["id"]) in {str(r["id"]) for r in before.get("death_records", [])}:
                    continue
                window = history.get(str(record["id"]), [])
                deaths.append({
                    **record,
                    "day": day,
                    "stage_at_death": window[-1]["stage"] if window else None,
                    "window_days": len(window),
                    "window_mean_consumed_kg": round(sum(w["consumed_kg"] for w in window) / max(1, len(window)), 5),
                    "window_mean_net_kcal": round(sum(w["net_kcal"] for w in window) / max(1, len(window)), 3),
                    "window_zero_intake_days": sum(1 for w in window if w["consumed_kg"] <= 0.0 and w["limit"] != "not_feeding"),
                    "window_bite_cap_days": sum(1 for w in window if w["limit"] == "bite_cap"),
                    "window_visible_viable_days": sum(1 for w in window if w["visible_max_kg"] >= adult_need_kg),
                    "window_reach3_viable_days": sum(1 for w in window if w["reach3_max_kg"] >= adult_need_kg),
                    "window_start_energy": window[0]["energy"] if window else None,
                    "final_day": window[-1] if window else None,
                })

            populated = [tuple(p["xy"]) for p in tick["physiology"].values()]
            world_cells = {(int(c["x"]), int(c["y"])): c for c in tick["world"]["cells"]}
            daily.append({
                "day": day,
                "alive_end": len(after["humans"]),
                "adults_end": sum(1 for p in after["humans"] if int(p["age_ticks"]) >= int(profile["maturity_ticks"])),
                "edible_start_kg": round(tick["edible_start_kg"], 3),
                "gross_plant_growth_kg": round(tick["gross_growth_kg"], 4),
                "net_edible_change_by_plants_kg": round(tick["edible_after_plants_kg"] - tick["edible_start_kg"], 4),
                "animal_grazing_kg": round(tick["edible_after_plants_kg"] - tick["edible_after_animals_kg"], 4),
                "human_intake_kg": round(intake_kg, 4),
                "edible_end_kg": round(tick["edible_end_kg"], 3),
                "cells_with_adult_daily_need": len(viable),
                "cells_with_bite_cap": sum(1 for kg in edible.values() if kg >= float(profile["bite_cap_kg"])),
                "max_cell_edible_kg": round(max(edible.values()), 4),
                "mean_temperature_c": round(sum(float(c["temperature"]) for c in world_cells.values()) / len(world_cells), 2),
                "occupied_cells": len(set(populated)),
                "desired_plant_growth_kg": round(tick.get("desired_growth_kg") or 0.0, 4),
                "growth_limited_cells": tick.get("growth_limited_cells") or {},
                **tick["stocks"],
            })

        final = sim.human_state()
        summary = {
            "seed": seed,
            "days": days,
            "agentus": len(final["humans"]),
            "births": int(final.get("cumulative_births", 0)),
            "deaths": int(final.get("cumulative_deaths", 0)),
            "deaths_by_cause": final.get("cumulative_deaths_by_cause", {}),
            "ledger_valid": sim.ledger.verify_chain(),
            "callback_calls": recorder.calls,
        }

    return {
        "summary": summary,
        "profile": {k: profile[k] for k in (
            "basal_energy_kcal_per_tick", "bite_cap_kg", "assimilation", "food_energy_kcal_per_kg",
            "move_energy_kcal_per_tick", "energy_capacity_kcal", "initial_energy_kcal",
            "nursing_energy_kcal_per_tick", "reproduction_energy_kcal", "maturity_ticks",
        )},
        "adult_daily_need_kg": adult_need_kg,
        "budgets_by_stage": {k: dict(v) for k, v in budgets.items()},
        "seasonal_adult": [{"year": y, "season": s, **dict(v)} for (y, s), v in sorted(seasonal.items())],
        "deaths": deaths,
        "lives": sorted(lives.values(), key=lambda r: r["id"]),
        "daily": daily,
    }


def run_ecology_only(seed: str, days: int = DAYS) -> dict:
    """Counterfactual: identical world/producers/consumers with no Agentus.

    Not a resource change: the human authority is simply absent, so founder
    bodies are not debited from producer biomass at genesis.
    """
    recorder = Recorder()
    config = replace(
        _config(seed),
        human_biology_enabled=False,
        human_cognition_enabled=False,
        human_actions_enabled=False,
        multi_population_enabled=False,
        human_calibration_enabled=False,
    )
    daily = []
    with instrumented(recorder):
        sim = GenesisSimulation(config)
        for day in range(days):
            sim.run(1)
            tick = recorder.tick
            daily.append({
                "day": day,
                "edible_start_kg": round(tick["edible_start_kg"], 3),
                "edible_end_kg": round(tick["edible_after_animals_kg"], 3),
                "gross_plant_growth_kg": round(tick["gross_growth_kg"], 4),
                "desired_plant_growth_kg": round(tick.get("desired_growth_kg") or 0.0, 4),
                "growth_limited_cells": tick.get("growth_limited_cells") or {},
                **tick["stocks"],
            })
    return {"seed": seed, "days": days, "daily": daily}


def aggregate(results: list[dict], counterfactual: list[dict]) -> dict:
    """Pooled findings across seeds, derived only from the recorded series."""
    profile = results[0]["profile"]
    need = results[0]["adult_daily_need_kg"]
    max_credit = float(profile["bite_cap_kg"]) * float(profile["food_energy_kcal_per_kg"]) * float(profile["assimilation"])
    adult = defaultdict(float)
    for result in results:
        for key, value in result["budgets_by_stage"].get("adult", {}).items():
            adult[key] += value
    days = adult["person_days"]
    deaths = [d for result in results for d in result["deaths"]]
    adult_deaths = [d for d in deaths if d["stage_at_death"] == "adult"]
    waves = {
        "before_day_300": [d for d in adult_deaths if d["day"] < 300],
        "from_day_300": [d for d in adult_deaths if d["day"] >= 300],
    }

    def wave_stats(rows: list[dict]) -> dict:
        n = max(1, len(rows))
        return {
            "deaths": len(rows),
            "day_range": [min(d["day"] for d in rows), max(d["day"] for d in rows)] if rows else None,
            "mean_window_consumed_kg": round(sum(d["window_mean_consumed_kg"] for d in rows) / n, 3),
            "mean_window_net_kcal": round(sum(d["window_mean_net_kcal"] for d in rows) / n, 1),
            "window_started_at_full_reserve": sum(1 for d in rows if (d["window_start_energy"] or 0) >= float(profile["energy_capacity_kcal"]) - float(profile["basal_energy_kcal_per_tick"]) - 1e-6),
            "final_day_no_viable_cell_on_map": sum(1 for d in rows if d["final_day"] and d["final_day"]["nearest_viable_steps"] is None),
            "final_day_viable_within_3_steps": sum(1 for d in rows if d["final_day"] and d["final_day"]["nearest_viable_steps"] is not None and d["final_day"]["nearest_viable_steps"] <= 3),
        }

    def edible(series: list[dict], day: int) -> float:
        return series[day]["edible_end_kg"]

    stock = []
    for result, cf in zip(results, counterfactual):
        cumulative = 0.0
        for row in result["daily"]:
            cumulative += row["human_intake_kg"]
            row["_cum"] = cumulative
        last = len(result["daily"]) - 1
        checkpoints = [d for d in (0, 120, 300, 364, 420, 600, last) if d <= last]
        stock.append({
            "seed": result["summary"]["seed"],
            "edible_kg_with_agentus": {d: edible(result["daily"], d) for d in checkpoints},
            "edible_kg_without_agentus": {d: edible(cf["daily"], d) for d in checkpoints},
            "cumulative_intake_kg": {d: round(result["daily"][d]["_cum"], 1) for d in checkpoints},
            "second_winter_min_edible_kg": min(r["edible_end_kg"] for r in result["daily"][365:]) if last >= 365 else None,
            "second_winter_min_viable_cells": min(r["cells_with_adult_daily_need"] for r in result["daily"][365:]) if last >= 365 else None,
            "total_gross_plant_growth_kg": round(sum(r["gross_plant_growth_kg"] for r in result["daily"]), 1),
            "total_animal_grazing_kg": round(sum(r["animal_grazing_kg"] for r in result["daily"]), 2),
            "max_woody_kg": max(r["woody_kg"] for r in result["daily"]),
            "growth_limited_cell_days": sum(sum(r["growth_limited_cells"].values()) for r in result["daily"]),
        })
        for row in result["daily"]:
            row.pop("_cum")

    return {
        "adult_daily_need_kg": round(need, 4),
        "adult_max_credited_kcal_per_day": round(max_credit, 1),
        "adult_max_surplus_over_basal_kcal_per_day": round(max_credit - float(profile["basal_energy_kcal_per_tick"]), 1),
        "reserve_days_of_basal": float(profile["energy_capacity_kcal"]) / float(profile["basal_energy_kcal_per_tick"]),
        "adult_per_day": {
            "person_days": int(days),
            "credited_kcal": round(adult["credited_kcal"] / days, 1),
            "basal_kcal": round(adult["basal_kcal"] / days, 1),
            "move_kcal": round(adult["move_kcal"] / days, 1),
            "thermal_kcal": round(adult["thermal_kcal"] / days, 1),
            "nursing_out_kcal": round(adult["nursing_out_kcal"] / days, 1),
            "saturation_waste_kcal": round(adult["saturation_waste_kcal"] / days, 1),
            "share_bite_cap_limited": round(adult["limit_bite_cap"] / days, 3),
            "share_cell_supply_limited": round(adult["limit_cell_supply"] / days, 3),
            "share_no_food_on_cell": round(adult["limit_no_food_on_cell"] / days, 4),
            "share_reserve_saturated": round(adult["saturated_days"] / days, 3),
        },
        "deaths_by_stage_and_cause": dict(sorted(
            ((f"{d['stage_at_death']}:{d['cause']}", sum(1 for e in deaths if (e["stage_at_death"], e["cause"]) == (d["stage_at_death"], d["cause"]))) for d in deaths)
        )),
        "adult_death_waves": {name: wave_stats(rows) for name, rows in waves.items()},
        "food_stock_by_seed": stock,
    }


DAILY_FIELDS = (
    "day", "alive_end", "adults_end", "edible_start_kg", "edible_end_kg", "gross_plant_growth_kg",
    "animal_grazing_kg", "human_intake_kg", "cells_with_adult_daily_need", "max_cell_edible_kg",
    "mean_temperature_c", "seed_kg", "detritus_kg", "woody_kg",
)


def _trim_daily(series: list[dict]) -> list[list]:
    """Compact the published daily series to the fields used in the summary."""
    return [[row.get(field) for field in DAILY_FIELDS] for row in series]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=DAYS)
    parser.add_argument("--seed", action="append", help="Run only this seed (repeatable)")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    seeds = args.seed or SEEDS
    with Pool(min(args.jobs, len(seeds))) as pool:
        results = pool.starmap(run_seed, [(seed, args.days) for seed in seeds])
        counterfactual = pool.starmap(run_ecology_only, [(seed, args.days) for seed in seeds])
    for result in results:
        print("FOOD_DIAGNOSIS_SEED:", json.dumps(result["summary"], sort_keys=True), flush=True)
    findings = aggregate(results, counterfactual)
    for result in results + counterfactual:
        result["daily"] = _trim_daily(result["daily"])
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({
            "days": args.days,
            "daily_fields": list(DAILY_FIELDS),
            "findings": findings,
            "seeds": results,
            "no_agentus_counterfactual": counterfactual,
        }, handle, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
