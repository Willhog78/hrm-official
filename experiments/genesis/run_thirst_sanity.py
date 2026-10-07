"""G10.4 thirst baseline: implementation sanity checks (read-only).

Not a study of whether thirst matters. This checks that the thirst drive
behaves sanely, comparing the baseline with the pre-G10.4 planner on the same
seeds:

1. Competition: thirst never overrides hunger that would kill sooner, and
   starvation deaths do not rise.
2. Locality: every thirst move is one step, toward visible water, remembered
   water, or exploration. No global knowledge.
3. Cause: remaining dehydration deaths are classified (dependent child, no
   water seen or remembered, or planner failure).
4. Pathology: oscillation, movement, crowding, water drawdown, births.

Instrumentation wraps the planner for measurement only; it returns exactly
what the planner returned.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hrm_genesis.human.planning as planning  # noqa: E402
from hrm_genesis import GenesisSimulation  # noqa: E402
from run_agentus_capacity_multiseed import config_for  # noqa: E402

SEEDS = ["agentus-demography-a", "agentus-demography-b", "agentus-demography-c", "agentus-demography-d"]


class Recorder:
    def __init__(self):
        self.counts = Counter()
        self.last_target: dict[str, tuple] = {}
        self.prev_origin: dict[str, tuple] = {}


def install(recorder: Recorder):
    original_thirst = planning._thirst_destination
    original_choose = planning.choose_destination

    def thirst(perception, cognition, forage_need, reserve_fraction):
        result = original_thirst(perception, cognition, forage_need, reserve_fraction)
        if "water_need_kg" in perception:
            ox, oy = map(int, perception["origin"])
            here = next(c for c in perception["cells"] if (int(c["x"]), int(c["y"])) == (ox, oy))
            dry_here = float(here["water_kg"]) < float(perception["water_need_kg"])
            hungry = forage_need > 0.0 and reserve_fraction < 0.75
            if dry_here:
                recorder.counts["dry_here_decisions"] += 1
            if result is not None:
                recorder.counts["thirst_moves"] += 1
                visible_now = {(int(c["x"]), int(c["y"])): c for c in perception["cells"]}
                target_food = float(visible_now.get(result, {}).get("expected_food_kg", visible_now.get(result, {}).get("food_kg", 0.0)))
                if hungry and float(perception["energy_days"]) < float(perception["hydration_days"]):
                    if target_food >= forage_need:
                        recorder.counts["thirst_and_hunger_met_together"] += 1
                    else:
                        recorder.counts["VIOLATION_thirst_over_more_urgent_hunger"] += 1
                dist = abs(result[0] - ox) + abs(result[1] - oy)
                if dist > 1:
                    recorder.counts["VIOLATION_thirst_move_beyond_one_step"] += 1
                visible = {(int(c["x"]), int(c["y"])): c for c in perception["cells"]}
                if result not in visible:
                    recorder.counts["VIOLATION_target_not_perceived"] += 1
                elif float(visible[result]["water_kg"]) >= float(perception["water_need_kg"]):
                    recorder.counts["thirst_to_visible_water"] += 1
                elif any(float(w) >= float(perception["water_need_kg"]) for _, _, w, _ in perception.get("remembered_water", [])):
                    recorder.counts["thirst_toward_remembered_water"] += 1
                else:
                    recorder.counts["thirst_exploring"] += 1
            elif dry_here and hungry and float(perception["energy_days"]) < float(perception["hydration_days"]):
                recorder.counts["hunger_prioritised_over_thirst"] += 1
        return result

    def choose(human, perception, cognition):
        result = original_choose(human, perception, cognition)
        hid = str(human.get("id", ""))
        origin = tuple(map(int, perception["origin"]))
        if result != origin:
            recorder.counts["moves"] += 1
            if recorder.prev_origin.get(hid) == result and recorder.last_target.get(hid) == origin:
                recorder.counts["immediate_back_and_forth"] += 1
        recorder.prev_origin[hid] = origin
        recorder.last_target[hid] = result
        return result

    planning._thirst_destination = thirst
    import hrm_genesis.human.biology as biology
    biology.choose_destination = choose
    return original_thirst, original_choose


def run(seed: str, arm: str, days: int) -> dict:
    recorder = Recorder()
    install(recorder)
    sim = GenesisSimulation(config_for(seed, arm))
    profile = sim.human_state()["physiology_profile"]
    dehydration = Counter()
    max_crowd = 0
    dry_occupied_days = 0
    agent_days = 0
    for _ in range(days):
        before = sim.human_state()
        wet_before = {(c["x"], c["y"]): c["surface_water_kg"] + c["soil_water_kg"] for c in sim.matter_state()["cells"]}
        sim.run(1)
        after = sim.human_state()
        cells = Counter((p["x"], p["y"]) for p in after["humans"])
        max_crowd = max([max_crowd] + list(cells.values()))
        agent_days += len(after["humans"])
        dry_occupied_days += sum(n for xy, n in cells.items() if wet_before.get(xy, 0.0) < 1.0)
        seen = {r["id"] for r in before.get("death_records", [])}
        people = {p["id"]: p for p in before["humans"]}
        for record in after.get("death_records", []):
            if record["id"] in seen:
                continue
            p = people[record["id"]]
            if record["cause"] == "energy":
                dehydration["starvation_age_years_" + str(int(p["age_ticks"]) // 365)] += 1
                continue
            if record["cause"] != "dehydration":
                continue
            x, y = int(p["x"]), int(p["y"])
            if int(p["age_ticks"]) < int(profile["independent_feeding_age_ticks"]):
                dehydration["dependent_child"] += 1
                continue
            need = float(profile["water_capacity_kg"]) - float(p["body_water_kg"]) + float(profile["water_loss_per_tick_kg"])
            visible = any(abs(cx - x) + abs(cy - y) <= 1 and w >= need for (cx, cy), w in wet_before.items())
            remembered = any(float(v.get("water_kg", 0.0)) >= need for v in p.get("cognition", {}).get("memory", {}).get("locations", {}).values())
            if visible:
                dehydration["adult_with_water_visible"] += 1
            elif remembered:
                dehydration["adult_with_water_remembered"] += 1
            else:
                dehydration["adult_no_water_known"] += 1
    final = sim.human_state()
    return {
        "seed": seed, "arm": arm, "days": days,
        "alive": len(final["humans"]), "births": final["cumulative_births"],
        "deaths_by_cause": final["cumulative_deaths_by_cause"],
        "death_context": dict(dehydration),
        "decisions": dict(recorder.counts),
        "max_agents_in_one_cell": max_crowd,
        "agent_days": agent_days,
        "agent_days_on_dry_cells": dry_occupied_days,
        "ledger_valid": sim.ledger.verify_chain(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default=SEEDS[0])
    parser.add_argument("--arm", default="v0", help="v0 (thirst baseline) or v0-nothirst")
    parser.add_argument("--days", type=int, default=730)
    args = parser.parse_args()
    print("THIRST_SANITY:", json.dumps(run(args.seed, args.arm, args.days), sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
