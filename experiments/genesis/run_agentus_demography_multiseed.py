from __future__ import annotations

import json
import argparse
from collections import Counter

from hrm_genesis import GenesisConfig, GenesisSimulation


SEEDS = [
    "agentus-demography-a",
    "agentus-demography-b",
    "agentus-demography-c",
    "agentus-demography-d",
]
DAYS = 730


def diagnose_tick(sim: GenesisSimulation, before: dict, seed: str, counters: Counter) -> None:
    """Read-only traces: global distances are measurements, never agent inputs."""
    after = sim.human_state()
    profile = before["physiology_profile"]
    prior = {str(p["id"]): p for p in before["humans"]}
    live = {str(p["id"]): p for p in after["humans"]}
    cells = sim.ecology_state()["cells"]
    need = float(profile["basal_energy_kcal_per_tick"]) / (
        float(profile["food_energy_kcal_per_kg"]) * float(profile["assimilation"])
    )
    edible = {(int(c["x"]), int(c["y"])): sum(c["plant_elements_kg"].values()) for c in cells}
    viable = [xy for xy, food in edible.items() if food >= need]
    for person in live.values():
        if person["sex"] != "female" or int(person["age_ticks"]) < int(profile["maturity_ticks"]):
            continue
        counters["adult_female_days"] += 1
        males = [p for p in live.values() if p["sex"] == "male" and int(p["age_ticks"]) >= int(profile["maturity_ticks"])]
        if any((p["x"], p["y"]) == (person["x"], person["y"]) for p in males):
            counters["adult_female_days_with_colocated_male"] += 1
        if float(person["energy"]) >= float(profile["reproduction_energy_kcal"]):
            counters["adult_female_days_with_reproduction_energy"] += 1
    old_deaths = {str(r["id"]) for r in before.get("death_records", [])}
    for record in after.get("death_records", []):
        if str(record["id"]) in old_deaths:
            continue
        person = prior[str(record["id"])]
        x, y = int(person["x"]), int(person["y"])
        nearby = [p for p in prior.values() if p["id"] != person["id"] and int(p["age_ticks"]) >= int(profile["maturity_ticks"]) and abs(int(p["x"]) - x) + abs(int(p["y"]) - y) <= 1]
        print("DEMOGRAPHY_DEATH_TRACE:", json.dumps({
            "seed": seed, **record,
            "pre_tick_xy": [x, y], "pre_tick_energy": person["energy"],
            "pre_tick_body_water_kg": person["body_water_kg"],
            "post_tick_edible_at_previous_cell_kg": edible[(x, y)],
            "post_tick_visible_max_edible_kg": max(food for (cx, cy), food in edible.items() if abs(cx-x)+abs(cy-y) <= 1),
            "post_tick_nearest_viable_food_steps": min((abs(cx-x)+abs(cy-y) for cx, cy in viable), default=None),
            "caregiver_alive_before": str(person.get("caregiver_id")) in prior,
            "caregiver_alive_after": str(person.get("caregiver_id")) in live,
            "nearby_adults_before": [p["id"] for p in nearby],
            "nearby_same_population_adults_before": [p["id"] for p in nearby if p.get("population_id") == person.get("population_id")],
        }, sort_keys=True), flush=True)


def summarize(sim: GenesisSimulation, seed: str) -> dict:
    humans = sim.human_state()
    people = list(humans["humans"])
    by_population = {}
    reproductive_populations = 0
    for person in people:
        pid = str(person.get("population_id", "unassigned"))
        bucket = by_population.setdefault(pid, {"female": 0, "male": 0, "total": 0})
        bucket[str(person["sex"])] += 1
        bucket["total"] += 1
    for bucket in by_population.values():
        if bucket["female"] > 0 and bucket["male"] > 0:
            reproductive_populations += 1

    return {
        "seed": seed,
        "days": DAYS,
        "agentus": len(people),
        "births": int(humans.get("cumulative_births", 0)),
        "deaths": int(humans.get("cumulative_deaths", 0)),
        "by_population_and_sex": by_population,
        "reproductive_populations": reproductive_populations,
        "extinct": len(people) == 0,
        "ledger_valid": sim.ledger.verify_chain(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnose", action="store_true", help="Trace daily deaths and adult partner contact without changing behavior")
    args = parser.parse_args()
    results = []
    for seed in SEEDS:
        config = GenesisConfig(
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
        sim = GenesisSimulation(config)
        counters = Counter()
        if args.diagnose:
            for day in range(DAYS):
                before = sim.human_state()
                sim.run(1)
                diagnose_tick(sim, before, seed, counters)
                if (day + 1) % 90 == 0:
                    print("DEMOGRAPHY_PROGRESS:", json.dumps({"seed": seed, "day": day + 1}, sort_keys=True), flush=True)
            print("DEMOGRAPHY_CONTACT:", json.dumps({"seed": seed, **counters}, sort_keys=True), flush=True)
        else:
            sim.run(DAYS)
        result = summarize(sim, seed)
        results.append(result)
        print("DEMOGRAPHY_SEED:", json.dumps(result, sort_keys=True), flush=True)

    print("DEMOGRAPHY_SUMMARY:", json.dumps({
        "seeds": len(results),
        "extinct_by_two_years": sum(1 for r in results if r["extinct"]),
        "zero_reproductive_populations": sum(1 for r in results if r["reproductive_populations"] == 0),
        "mean_agentus": sum(r["agentus"] for r in results) / len(results),
        "total_births": sum(r["births"] for r in results),
        "all_ledgers_valid": all(r["ledger_valid"] for r in results),
    }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
